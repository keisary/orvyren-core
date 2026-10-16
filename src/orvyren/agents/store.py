"""``agents.store`` — immutable content-addressed store of LLM exchanges (L2.6).

The store is the ground of the REPLAY-JOURNAL demo (DOC2 §5.2.2, DOC4 L2.6):
a replayed run must rebuild the **identical** :class:`LLMResult`, so every
prompt, every raw answer and every accounting figure is archived, addressed
by hash. Nothing is ever rewritten:

- **response blobs** — ``blobs/<sha256(raw utf-8)>.txt``: the raw answer text
  of one LLM call, written by the backends and strictly re-hashable;
- **prompt blobs** — ``blobs/<prompt_hash>.txt``: the prompt material
  ``{"payload": …, "system_prompt": …}`` in canonical JSON; ``prompt_hash``
  is the hash of the *envelope* ``(role, role_version, schema_id,
  system_prompt, payload)`` — recomputable in :meth:`ResponseStore.verify`
  through the call line that references it;
- ``calls.jsonl`` — one JSON line per call (at least ``record_id``,
  ``prompt_hash``, ``response_hash``, ``role``, ``role_version``,
  ``schema_id``, ``ts_utc`` plus the tokens/cost/latency accounting).

Saving different content under an existing hash raises ``E_STORE_IMMUTABLE``.

Standard library only (json / hashlib / pathlib).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from . import contracts

__all__ = [
    "ResponseStore",
    "prompt_hash",
    "response_hash",
    "E_STORE_IMMUTABLE",
    "E_STORE_CALL_INCOMPLETE",
    "E_STORE_MISSING_BLOB",
]

#: A different body was written under an existing content address.
E_STORE_IMMUTABLE = "E_STORE_IMMUTABLE"
#: A call line misses one of the required columns.
E_STORE_CALL_INCOMPLETE = "E_STORE_CALL_INCOMPLETE"
#: A blob addressed by this hash does not exist.
E_STORE_MISSING_BLOB = "E_STORE_MISSING_BLOB"

#: Columns every call line MUST carry (the journal's llm accounting, B1 §3.4).
REQUIRED_CALL_FIELDS: Tuple[str, ...] = (
    "record_id", "prompt_hash", "response_hash", "role", "role_version",
    "schema_id", "ts_utc",
)

_HASH_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_PROMPT_BLOB_KEYS = frozenset({"payload", "system_prompt"})


def _prompt_envelope(role: str, role_version: str, schema_id: str,
                     system_prompt: str, payload: Any) -> Dict[str, Any]:
    """The exact object whose canonical JSON is hashed into a prompt hash."""
    return {
        "payload": payload,
        "role": role,
        "role_version": role_version,
        "schema_id": schema_id,
        "system_prompt": system_prompt,
    }


def prompt_hash(role: str, role_version: str, schema_id: str,
                system_prompt: str, payload: Any) -> str:
    """SHA-256 (hex) of the canonical envelope of one prompt.

    The envelope pins the prompt **text**, its role, its version and the
    output schema id: bumping a prompt version invalidates every recording
    made under the previous one (that is what makes replay honest).
    """
    text = contracts.canonical_json(
        _prompt_envelope(role, role_version, schema_id, system_prompt, payload))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def response_hash(raw: str) -> str:
    """Address of a raw response blob: sha256 of its UTF-8 bytes."""
    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()


class ResponseStore:
    """Immutable, content-addressed store rooted at ``root_dir``.

    Writes are create-only (``E_STORE_IMMUTABLE`` on a conflicting rewrite);
    reads are pure. :meth:`verify` recomputes every blob of the store.
    """

    def __init__(self, root_dir: Any) -> None:
        self.root = Path(root_dir)
        self.blobs_dir = self.root / "blobs"
        self.calls_path = self.root / "calls.jsonl"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)

    # -- addressing ---------------------------------------------------------
    def hash_prompt(self, role: str, role_version: str, schema_id: str,
                    system_prompt: str, payload: Mapping[str, Any]) -> str:
        """Content address of one prompt (module-level :func:`prompt_hash`)."""
        return prompt_hash(role, role_version, schema_id, system_prompt, payload)

    def blob_path(self, blob_hash: str) -> Path:
        """Path of the blob addressed by ``blob_hash``."""
        return self.blobs_dir / ("%s.txt" % blob_hash)

    # -- writes (create-only) ----------------------------------------------
    def save_prompt(self, prompt_hash: str, system_prompt: str,
                    payload: Mapping[str, Any]) -> Path:
        """Archive one prompt's material under its envelope hash."""
        text = contracts.canonical_json(
            {"payload": payload, "system_prompt": system_prompt})
        return self._write_blob(prompt_hash, text)

    def save_response(self, response_hash: str, raw: str) -> Path:
        """Archive one raw answer under the sha256 of its UTF-8 bytes."""
        return self._write_blob(response_hash, str(raw))

    def _write_blob(self, blob_hash: str, text: str) -> Path:
        path = self.blob_path(blob_hash)
        data = text.encode("utf-8")
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(
                    "%s: blobs/%s.txt already exists with different content"
                    % (E_STORE_IMMUTABLE, blob_hash))
            return path
        path.write_bytes(data)
        return path

    def record_call(self, entry: Mapping[str, Any]) -> Dict[str, Any]:
        """Append one JSONL call line (validating the required columns)."""
        missing = [key for key in REQUIRED_CALL_FIELDS if key not in entry]
        if missing:
            raise ValueError("%s: missing %s"
                             % (E_STORE_CALL_INCOMPLETE, ", ".join(missing)))
        line = contracts.canonical_json(dict(entry))
        with self.calls_path.open("ab") as handle:
            handle.write((line + "\n").encode("utf-8"))
        return dict(entry)

    # -- reads --------------------------------------------------------------
    def calls(self) -> List[Dict[str, Any]]:
        """All parsable call lines, in append order (unparsable ones skipped)."""
        if not self.calls_path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        for line in self.calls_path.read_bytes().decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
        return entries

    def find_call(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """The last call recorded for this prompt hash, or ``None``."""
        found: Optional[Dict[str, Any]] = None
        for entry in self.calls():
            if entry.get("prompt_hash") == prompt_hash:
                found = entry
        return found

    def get_response(self, response_hash: str) -> str:
        """The raw answer archived under ``response_hash``."""
        path = self.blob_path(response_hash)
        if not path.exists():
            raise FileNotFoundError("%s: %s" % (E_STORE_MISSING_BLOB, response_hash))
        return path.read_bytes().decode("utf-8")

    # -- audit --------------------------------------------------------------
    def verify(self) -> Tuple[bool, List[str]]:
        """Recompute every blob; report problems (``(ok, problems)``).

        - a blob whose content hashes to its file name is verified (all
          response blobs are checked this way);
        - a prompt blob (canonical JSON ``{"payload", "system_prompt"}``) is
          re-hashed from its content plus the ``role``/``role_version``/
          ``schema_id`` of the call line addressing it — a rewritten prompt,
          an orphan prompt blob or a tampered response blob is reported.
        """
        problems: List[str] = []
        by_prompt: Dict[str, Dict[str, Any]] = {}
        for entry in self.calls():
            key = str(entry.get("prompt_hash", ""))
            if key:
                by_prompt[key] = entry  # last line wins, like find_call
        for path in sorted(self.blobs_dir.glob("*.txt")):
            name = path.stem
            data = path.read_bytes()
            if not _HASH_RE.match(name):
                problems.append("bad blob name: %s" % path.name)
                continue
            if hashlib.sha256(data).hexdigest() == name:
                continue
            if self._is_recorded_prompt_blob(data, name, by_prompt):
                continue
            problems.append(
                "blob %s does not hash to its name and is not the prompt of a "
                "recorded call" % path.name)
        return (not problems), problems

    @staticmethod
    def _is_recorded_prompt_blob(data: bytes, name: str,
                                 by_prompt: Mapping[str, Dict[str, Any]]) -> bool:
        entry = by_prompt.get(name)
        if entry is None:
            return False
        try:
            text = data.decode("utf-8")
            parsed = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return False
        if not isinstance(parsed, dict) or set(parsed) != _PROMPT_BLOB_KEYS:
            return False
        if contracts.canonical_json(parsed) != text:
            return False
        rebuilt = prompt_hash(entry.get("role", ""), entry.get("role_version", ""),
                              entry.get("schema_id", ""),
                              parsed.get("system_prompt"), parsed.get("payload"))
        return rebuilt == name
