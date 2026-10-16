"""``agents.llm`` — LLM backends of the bounded MA-B loop (L2.5/L2.6).

Two interchangeable backends behind the frozen ``contracts.LLMBackend``
protocol:

- :class:`RecordedBackend` — REPLAY-JOURNAL mode: the answer comes from the
  immutable :class:`agents.store.ResponseStore`, **bit-identical** to the run
  that recorded it (same tokens, cost, latency, ``ts_utc``, provenance);
- :class:`LiveBackend` — live OpenAI-compatible JSON-mode calls implementing
  the frozen recovery-by-class policy of DOC2 §5.2.4: transport errors and
  HTTP ≥ 500 retried (≤ 2, backoff), HTTP 429 gives one backoff then switches
  provider, then the role's ``fallbacks`` chain is tried (keyless or
  URL-less candidates skipped); all exhausted → ``E_LLM_ALL_PROVIDERS_FAILED``.
  An empty answer (documented DeepSeek pitfall) is non-conforming
  (``E_LLM_EMPTY_RESPONSE``) — never a guess downstream — and invalid JSON is
  ``E_LLM_BAD_JSON``.

Both backends fill ``provider`` / ``model`` / ``model_version_pinned`` /
``temperature`` on **every** result (even errors), so journal lines always
document provenance (B1 §5.5). The models config is the frozen, pinned,
dated file ``config/models.json`` (DOC2 §5.2.2).

Standard library only (``urllib`` for the default transport — injectable).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from . import contracts
from .store import ResponseStore, prompt_hash, response_hash

__all__ = [
    "load_models_config",
    "compute_cost",
    "RecordedBackend",
    "LiveBackend",
]

#: Where the frozen config lives, relative to the repository root.
CONFIG_RELATIVE_PATH: Tuple[str, ...] = ("config", "models.json")
#: Expected schema id of the config file.
CONFIG_SCHEMA_ID = "orvyren/models-config/v1"

DEFAULT_TIMEOUT_S = 60.0
MAX_TRANSIENT_RETRIES = 2      # transport errors and HTTP >= 500
MAX_RATE_LIMIT_RETRIES = 1     # HTTP 429: one backoff, then switch provider
BACKOFF_BASE_S = 0.5

REQUIRED_MODEL_FIELDS: Tuple[str, ...] = (
    "provider", "api_model", "pinned_version", "temperature", "api_key_env",
    "prices_usd_per_mtok",
)
REQUIRED_PRICE_KEYS: Tuple[str, ...] = ("cache_in", "in", "out")


# ---------------------------------------------------------------------------
# Config (DOC2 §5.2.2): load + strict validation, E_CONFIG_* errors.
# ---------------------------------------------------------------------------
def _find_repo_config(start: Path) -> Path:
    """Walk up from ``start`` looking for ``config/models.json``."""
    for parent in [start] + list(start.parents):
        candidate = parent.joinpath(*CONFIG_RELATIVE_PATH)
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "E_CONFIG_NOT_FOUND: config/models.json not found above %s" % start)


def _validate_config(config: Any, source: Path) -> None:
    """Strict validation of the pinned models config (E_CONFIG_* codes)."""

    def fail(code: str, message: str) -> None:
        raise ValueError("%s: %s (%s)" % (code, message, source))

    if not isinstance(config, dict):
        fail("E_CONFIG_INVALID", "top level must be a JSON object")
    for key in ("schema", "roles", "models"):
        if key not in config:
            fail("E_CONFIG_INVALID", "missing top-level key %r" % key)
    if not str(config.get("schema", "")).strip():
        fail("E_CONFIG_INVALID", "empty schema id")
    roles, models = config.get("roles"), config.get("models")
    if not isinstance(roles, dict) or not roles:
        fail("E_CONFIG_INVALID", "roles must be a non-empty object")
    if not isinstance(models, dict) or not models:
        fail("E_CONFIG_INVALID", "models must be a non-empty object")

    for key, model in models.items():
        if not isinstance(model, dict):
            fail("E_CONFIG_MODEL_INCOMPLETE", "model %r is not an object" % key)
        for field in REQUIRED_MODEL_FIELDS:
            if field not in model:
                fail("E_CONFIG_MODEL_INCOMPLETE",
                     "model %r misses %r" % (key, field))
        for field in ("provider", "api_model", "pinned_version", "api_key_env"):
            if not str(model.get(field, "")).strip():
                fail("E_CONFIG_MODEL_INCOMPLETE",
                     "model %r has an empty %r" % (key, field))
        temperature = model.get("temperature")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            fail("E_CONFIG_MODEL_INCOMPLETE",
                 "model %r temperature must be a number" % key)
        prices = model.get("prices_usd_per_mtok")
        if not isinstance(prices, dict):
            fail("E_CONFIG_MODEL_INCOMPLETE",
                 "model %r prices_usd_per_mtok must be an object" % key)
        for price_key in REQUIRED_PRICE_KEYS:
            price = prices.get(price_key)
            if (isinstance(price, bool) or not isinstance(price, (int, float))
                    or price < 0):
                fail("E_CONFIG_MODEL_INCOMPLETE",
                     "model %r price %r must be a non-negative number"
                     % (key, price_key))
        base_url = str(model.get("base_url", "") or "")
        base_url_note = str(model.get("base_url_note", "") or "")
        if not base_url.strip() and not base_url_note.strip():
            fail("E_CONFIG_BASE_URL",
                 "model %r has an empty base_url without base_url_note" % key)

    for role, spec in roles.items():
        if not isinstance(spec, dict):
            fail("E_CONFIG_ROLE_INCOMPLETE", "role %r is not an object" % role)
        model_key = str(spec.get("model_key", "") or "").strip()
        if not model_key:
            fail("E_CONFIG_ROLE_INCOMPLETE", "role %r misses model_key" % role)
        if "fallbacks" not in spec:
            fail("E_CONFIG_ROLE_INCOMPLETE", "role %r misses fallbacks" % role)
        fallbacks = spec.get("fallbacks")
        if not isinstance(fallbacks, (list, tuple)):
            fail("E_CONFIG_ROLE_INCOMPLETE",
                 "role %r fallbacks must be a list" % role)
        for referenced in [model_key] + list(fallbacks):
            if referenced not in models:
                fail("E_CONFIG_MODEL_UNKNOWN",
                     "role %r references unknown model %r" % (role, referenced))


def load_models_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load and validate the pinned models config.

    Without ``path``, the file is located by walking up from this module's
    ``__file__`` to the repository root (``config/models.json``). Strict
    validation: top keys ``schema``/``roles``/``models``; every role's
    ``model_key`` and ``fallbacks`` exist in ``models``; every model carries
    ``provider``/``api_model``/``pinned_version``/``temperature``/
    ``api_key_env``/``prices_usd_per_mtok``; ``base_url`` may be empty only
    with a ``base_url_note``. Failures raise ``E_CONFIG_*`` value errors.
    """
    if path is None:
        source = _find_repo_config(Path(__file__).resolve())
    else:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError("E_CONFIG_NOT_FOUND: %s" % source)
    try:
        config = json.loads(source.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("E_CONFIG_INVALID: %s: %s" % (source, exc))
    _validate_config(config, source)
    return config


# ---------------------------------------------------------------------------
# Cost (DOC2 §5.2.2).
# ---------------------------------------------------------------------------
def compute_cost(model_cfg: Mapping[str, Any], tokens_in: int,
                 cached_in: int, tokens_out: int) -> float:
    """Cost in USD of one call at the frozen per-Mtok prices.

    ``tokens_in`` is the **total** prompt-token count (DeepSeek
    ``prompt_tokens``); ``cached_in`` is its cached subset
    (``prompt_cache_hit_tokens``), billed at the discounted ``cache_in``
    rate. Anchor: the frozen target profile (60k missed + 200k cached input
    tokens, 6k output, DeepSeek flash off-peak) costs exactly 0.0132 USD.
    """
    prices = model_cfg["prices_usd_per_mtok"]
    cached = max(0, int(cached_in))
    missed = max(0, int(tokens_in) - cached)
    return (missed * float(prices["in"])
            + cached * float(prices["cache_in"])
            + max(0, int(tokens_out)) * float(prices["out"])) / 1_000_000.0


# ---------------------------------------------------------------------------
# Small helpers shared by both backends.
# ---------------------------------------------------------------------------
def _role_model_chain(config: Mapping[str, Any], role: str) -> Optional[List[str]]:
    spec = (config.get("roles") or {}).get(role)
    if not isinstance(spec, Mapping):
        return None
    model_key = str(spec.get("model_key", "") or "").strip()
    if not model_key:
        return None
    return [model_key] + [str(k) for k in (spec.get("fallbacks") or [])]


def _model_meta(config: Mapping[str, Any], model_key: str) -> Dict[str, Any]:
    cfg = (config.get("models") or {}).get(model_key) or {}
    return {
        "provider": str(cfg.get("provider", "")),
        "model": str(model_key),
        "model_version_pinned": str(cfg.get("pinned_version", "")),
        "temperature": float(cfg.get("temperature", 0.0) or 0.0),
    }


def _role_meta(config: Mapping[str, Any], role: str) -> Dict[str, Any]:
    chain = _role_model_chain(config, role)
    if chain is None:
        return {"provider": "", "model": "", "model_version_pinned": "",
                "temperature": 0.0}
    return _model_meta(config, chain[0])


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record_id(prompt_hash: str, response_hash: str, ts_utc: str) -> str:
    digest = hashlib.sha256(
        ("%s:%s:%s" % (prompt_hash, response_hash, ts_utc)).encode("utf-8"))
    return "rec-" + digest.hexdigest()[:24]


# ---------------------------------------------------------------------------
# Recorded backend (REPLAY-JOURNAL).
# ---------------------------------------------------------------------------
class RecordedBackend(contracts.LLMBackend):
    """Replay the recorded answers — no network, bit-identical results.

    A prompt whose hash is not in the store fails closed with
    ``E_LLM_NOT_RECORDED:<prompt_hash>``; a recorded answer is returned with
    the **recorded** tokens / cost / latency / ``ts_utc`` / provenance copied
    from the call line, so a journaled run hashes identically across replays.
    """

    def __init__(self, store: ResponseStore,
                 config: Optional[Mapping[str, Any]] = None) -> None:
        self.store = store
        self.config = config if config is not None else load_models_config()

    def find_call(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """The call line recorded for this prompt hash, or ``None``."""
        return self.store.find_call(prompt_hash)

    def complete(self, *, role: str, role_version: str, schema_id: str,
                 system_prompt: str, payload: Mapping[str, Any]
                 ) -> contracts.LLMResult:
        meta = _role_meta(self.config, role)
        if _role_model_chain(self.config, role) is None:
            return contracts.LLMResult(ok=False, error="E_LLM_UNKNOWN_ROLE:%s" % role)
        p_hash = self.store.hash_prompt(role, role_version, schema_id,
                                        system_prompt, payload)
        entry = self.store.find_call(p_hash)
        if entry is None:
            return contracts.LLMResult(
                ok=False, error="E_LLM_NOT_RECORDED:%s" % p_hash,
                prompt_hash=p_hash, **meta)
        r_hash = str(entry.get("response_hash", ""))
        try:
            raw = self.store.get_response(r_hash)
        except (FileNotFoundError, OSError):
            return contracts.LLMResult(
                ok=False, error="E_LLM_MISSING_BLOB:%s" % r_hash,
                prompt_hash=p_hash, response_hash=r_hash, **meta)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            data = None
        if not isinstance(data, dict):
            return contracts.LLMResult(
                ok=False, raw=raw, error="E_LLM_BAD_JSON",
                prompt_hash=p_hash, response_hash=r_hash, **meta)
        return contracts.LLMResult(
            ok=True, raw=raw, data=data, error="",
            provider=str(entry.get("provider", meta["provider"])),
            model=str(entry.get("model", meta["model"])),
            model_version_pinned=str(
                entry.get("model_version_pinned", meta["model_version_pinned"])),
            temperature=float(entry.get("temperature", meta["temperature"])),
            tokens_in=int(entry.get("tokens_in", 0) or 0),
            cached_in=int(entry.get("cached_in", 0) or 0),
            tokens_out=int(entry.get("tokens_out", 0) or 0),
            cost_usd=float(entry.get("cost_usd", 0.0) or 0.0),
            latency_ms=int(entry.get("latency_ms", 0) or 0),
            prompt_hash=p_hash, response_hash=r_hash,
            ts_utc=str(entry.get("ts_utc", "")),
        )


# ---------------------------------------------------------------------------
# Default transport (OpenAI-compatible POST via urllib).
# ---------------------------------------------------------------------------
def _urllib_post(url: str, headers: Mapping[str, str], body_bytes: bytes,
                 timeout: float) -> Tuple[int, str]:
    """POST ``body_bytes`` and return ``(status_code, response_text)``.

    HTTP error statuses come back as values (not exceptions); transport
    failures keep raising — the caller retries them (≤ 2).
    """
    request = urllib.request.Request(url, data=body_bytes,
                                     headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Live backend (OpenAI-compatible JSON mode).
# ---------------------------------------------------------------------------
class LiveBackend(contracts.LLMBackend):
    """Live calls against the pinned models, with frozen recovery classes.

    Recovery by class (DOC2 §5.2.4): transport error or HTTP ≥ 500 → retry
    (≤ 2, injected sleeper); HTTP 429 → one backoff then switch provider;
    other non-2xx → switch provider; provider chain exhausted →
    ``E_LLM_ALL_PROVIDERS_FAILED``. Content failures are terminal:
    ``E_LLM_EMPTY_RESPONSE`` / ``E_LLM_BAD_JSON`` (the loop re-prompts or
    quarantines — the backend never guesses). On success with a ``store``,
    the prompt, the raw answer and the call line are archived, which is what
    :class:`RecordedBackend` replays.
    """

    def __init__(self, config: Optional[Mapping[str, Any]] = None,
                 store: Optional[ResponseStore] = None,
                 env: Optional[Mapping[str, str]] = None,
                 http_post=None, clock=None, sleeper=None,
                 timeout: float = DEFAULT_TIMEOUT_S) -> None:
        self.config = config if config is not None else load_models_config()
        self.store = store
        self.env = dict(os.environ) if env is None else {
            str(k): str(v) for k, v in dict(env).items()}
        self.http_post = http_post if http_post is not None else _urllib_post
        self.clock = clock if clock is not None else time.monotonic
        self.sleeper = sleeper if sleeper is not None else time.sleep
        self.timeout = float(timeout)

    # -- protocol -----------------------------------------------------------
    def complete(self, *, role: str, role_version: str, schema_id: str,
                 system_prompt: str, payload: Mapping[str, Any]
                 ) -> contracts.LLMResult:
        chain = _role_model_chain(self.config, role)
        if chain is None:
            return contracts.LLMResult(ok=False, error="E_LLM_UNKNOWN_ROLE:%s" % role)
        meta = _model_meta(self.config, chain[0])
        p_hash = prompt_hash(role, role_version, schema_id, system_prompt, payload)
        ctx = {"role": role, "role_version": role_version, "schema_id": schema_id,
               "system_prompt": system_prompt, "payload": payload,
               "prompt_hash": p_hash, "t_start": self.clock()}
        failures: List[str] = []
        had_key = False
        for model_key in chain:
            model_cfg = (self.config.get("models") or {}).get(model_key) or {}
            api_key = str(self.env.get(
                str(model_cfg.get("api_key_env", "")), "") or "").strip()
            if not api_key:
                failures.append("%s:no_key" % model_key)
                continue
            had_key = True
            base_url = str(model_cfg.get("base_url", "") or "").strip()
            if not base_url:
                failures.append("%s:no_base_url" % model_key)
                continue
            result, motif = self._call_model(model_key, model_cfg, api_key,
                                             base_url, ctx)
            if result is not None:
                return result
            failures.append("%s:%s" % (model_key, motif))
        error = "E_LLM_NO_KEY" if not had_key else "E_LLM_ALL_PROVIDERS_FAILED"
        return contracts.LLMResult(ok=False, error=error, prompt_hash=p_hash,
                                   **meta)

    # -- one candidate model -------------------------------------------------
    def _call_model(self, model_key: str, model_cfg: Mapping[str, Any],
                    api_key: str, base_url: str, ctx: Mapping[str, Any]
                    ) -> Tuple[Optional[contracts.LLMResult], str]:
        """Attempt one candidate: returns a terminal result or a fail motif."""
        url = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model_cfg.get("api_model"),
            "temperature": float(model_cfg.get("temperature", 0.0) or 0.0),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": ctx["system_prompt"]},
                {"role": "user", "content": contracts.canonical_json(ctx["payload"])},
            ],
        }
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer %s" % api_key}
        body_bytes = contracts.canonical_json(body).encode("utf-8")
        meta = _model_meta(self.config, model_key)
        transient, rate_limited = 0, 0
        while True:
            status, text, transport_error = None, "", ""
            try:
                pair = self.http_post(url, headers, body_bytes, self.timeout)
                status, text = int(pair[0]), str(pair[1])
            except Exception as exc:  # transport failure -> bounded retry
                transport_error = type(exc).__name__
            if status is None or status >= 500:
                if transient < MAX_TRANSIENT_RETRIES:
                    transient += 1
                    self.sleeper(BACKOFF_BASE_S * transient)
                    continue
                return None, ("transport:%s" % transport_error
                              if status is None else "http_%d" % status)
            if status == 429:
                if rate_limited < MAX_RATE_LIMIT_RETRIES:
                    rate_limited += 1
                    self.sleeper(BACKOFF_BASE_S * rate_limited)
                    continue
                return None, "http_429"
            if not 200 <= status < 300:
                return None, "http_%d" % status
            return self._parse_success(text, model_cfg, meta, ctx), ""

    # -- response parsing -----------------------------------------------------
    def _parse_success(self, text: str, model_cfg: Mapping[str, Any],
                       meta: Mapping[str, Any], ctx: Mapping[str, Any]
                       ) -> contracts.LLMResult:
        try:
            envelope = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            envelope = None
        content = None
        usage: Mapping[str, Any] = {}
        if isinstance(envelope, dict):
            try:
                content = envelope["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = None
            if isinstance(envelope.get("usage"), dict):
                usage = envelope["usage"]
        if content is None:
            return contracts.LLMResult(
                ok=False, raw=str(text), error="E_LLM_BAD_RESPONSE",
                prompt_hash=ctx["prompt_hash"], **meta)
        content = str(content)
        tokens_in = int(usage.get("prompt_tokens") or 0)
        cached_in = int(usage.get("prompt_cache_hit_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        cost_usd = compute_cost(model_cfg, tokens_in, cached_in, tokens_out)
        latency_ms = int(round((self.clock() - ctx["t_start"]) * 1000.0))
        if not content.strip():
            # Documented DeepSeek pitfall: a 200 with empty content is
            # non-conforming (DOC2 §5.2.4) — never a guess downstream.
            return contracts.LLMResult(
                ok=False, raw=content, error="E_LLM_EMPTY_RESPONSE",
                tokens_in=tokens_in, cached_in=cached_in, tokens_out=tokens_out,
                cost_usd=cost_usd, latency_ms=latency_ms,
                prompt_hash=ctx["prompt_hash"], **meta)
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            data = None
        if not isinstance(data, dict):
            return contracts.LLMResult(
                ok=False, raw=content, error="E_LLM_BAD_JSON",
                tokens_in=tokens_in, cached_in=cached_in, tokens_out=tokens_out,
                cost_usd=cost_usd, latency_ms=latency_ms,
                prompt_hash=ctx["prompt_hash"], **meta)
        ts_utc = _utc_now()
        r_hash = response_hash(content)
        if self.store is not None:
            self.store.save_prompt(ctx["prompt_hash"], ctx["system_prompt"],
                                   ctx["payload"])
            self.store.save_response(r_hash, content)
            self.store.record_call({
                "record_id": _record_id(ctx["prompt_hash"], r_hash, ts_utc),
                "prompt_hash": ctx["prompt_hash"],
                "response_hash": r_hash,
                "role": ctx["role"],
                "role_version": ctx["role_version"],
                "schema_id": ctx["schema_id"],
                "ts_utc": ts_utc,
                "provider": meta["provider"],
                "model": meta["model"],
                "model_version_pinned": meta["model_version_pinned"],
                "temperature": meta["temperature"],
                "tokens_in": tokens_in,
                "cached_in": cached_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            })
        return contracts.LLMResult(
            ok=True, raw=content, data=data, error="",
            provider=meta["provider"], model=meta["model"],
            model_version_pinned=meta["model_version_pinned"],
            temperature=meta["temperature"],
            tokens_in=tokens_in, cached_in=cached_in, tokens_out=tokens_out,
            cost_usd=cost_usd, latency_ms=latency_ms,
            prompt_hash=ctx["prompt_hash"], response_hash=r_hash,
            ts_utc=ts_utc)
