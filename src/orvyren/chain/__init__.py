"""``orvyren.chain`` — shared ``run_id`` run chain (event-sourcing + hashed
artifact contracts).

The repository's pipeline is snapshot -> agent search (hash-chained journal) ->
deterministic decision (RDOF) -> permission policy -> on-chain executor ->
evaluation. Audit (P0-2): those stages were disjoint paths — no shared run
identity, no artifact contract between stages. This module is the missing
piece: **one run identity, one append-only event log, one hashed artifact
manifest shared by decision, policy and executor**.

Design (applied event-sourcing research):

* ``run_id`` — a unique, human-readable, never-reused identifier
  (:func:`new_run_id`). A re-run gets a **new** ``run_id`` and carries the
  original one as ``parent_run_id`` — an identifier is never recycled;
* **events** — :meth:`RunChain.record` appends one JSONL line per event,
  every line carries ``run_id`` / ``parent_run_id`` / ``case_id`` / ``stage`` /
  ``ts_utc`` / ``prev_hash`` and is chained by hash (canonical JSON + SHA-256,
  the ``orvyren.agents.journal.entry_hash`` pattern, duplicated locally on
  purpose — this module must not depend on the agents package). ``ts_utc`` is
  the single signed time field of the line; caller payloads carry **no**
  wall-clock so hashed content stays reproducible;
* **artifacts** — :meth:`RunChain.write_artifact` writes canonical JSON to
  ``root_dir/<stage>/<name>`` (atomic: temporary file + ``os.replace``,
  ``newline="\\n"``) and records ``{stage, sha256, bytes}`` in
  ``manifest.json``. Artifacts are immutable: rewriting a name with a
  different content is a contract violation;
* **handoffs** — :meth:`RunChain.handoff` verifies every named artifact
  against the manifest (present + sha256 valid) before a stage boundary is
  crossed. Any violation raises :class:`ChainContractError` — **fail-closed**:
  the transition stops, nothing is assumed;
* :meth:`RunChain.verify` recomputes the whole event chain and the sha256 of
  every manifest artifact. Contract failure = run stop, never a repair.

Standard library only (``json``, ``hashlib``, ``os``, ``secrets``,
``tempfile``, ``datetime``).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Sequence, Tuple

__all__ = [
    "GENESIS_HASH",
    "SCHEMA_MANIFEST",
    "SCHEMA_ARTIFACT",
    "E_CHAIN_CONTRACT",
    "E_CHAIN_RUN_ID_REQUIRED",
    "ChainContractError",
    "ChainRunIdRequired",
    "new_run_id",
    "RunChain",
]

#: First line of an event chain.
GENESIS_HASH = "0" * 64

#: Schema versions of the two persisted documents.
SCHEMA_MANIFEST = "orvyren-run-chain/v1"
SCHEMA_ARTIFACT = "orvyren-run-artifact/v1"

#: Stable error codes (machine-checked, never renamed).
E_CHAIN_CONTRACT = "E_CHAIN_CONTRACT"
E_CHAIN_RUN_ID_REQUIRED = "E_CHAIN_RUN_ID_REQUIRED"

#: Event line hash field names excluded from the hashed serialisation
#: (``prev_hash`` links, ``event_hash`` is the digest itself) — the local
#: twin of ``orvyren.agents.journal.entry_hash`` (prev_hash excluded).
_HASH_EXCLUDED = ("prev_hash", "event_hash")

#: Plain identifier policy for run identifiers (also used in file paths).
_ID_SEPARATORS = ("", ".", "..")


class ChainContractError(ValueError):
    """Fail-closed run-chain contract violation.

    Stable code ``E_CHAIN_CONTRACT`` (``ChainRunIdRequired`` narrows it to
    ``E_CHAIN_RUN_ID_REQUIRED``). A contract failure is always a stop: the
    caller never repairs, never assumes, never reuses an identifier.
    """

    code = E_CHAIN_CONTRACT

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code or type(self).code


class ChainRunIdRequired(ChainContractError):
    """Real (``--execute``) run attempted without an explicit ``run_id``.

    Real execution is never auto-identified: the operator names the run
    (and its ``parent_run_id`` when replaying) or the run is refused
    before the first tick (``E_CHAIN_RUN_ID_REQUIRED``).
    """

    code = E_CHAIN_RUN_ID_REQUIRED


# --------------------------------------------------------------------------
# Hashing and I/O primitives (canonical JSON + SHA-256, atomic writes).
# --------------------------------------------------------------------------
def _canonical_json(payload: Any) -> str:
    """Canonical serialization: sorted keys, fixed separators, UTF-8."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _event_hash(line: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical event serialisation (hash fields excluded)."""
    payload = {key: value for key, value in line.items()
               if key not in _HASH_EXCLUDED}
    return _sha256_text(_canonical_json(payload))


def _utc_stamp() -> str:
    """The single time field of an event line (UTC, microsecond precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _atomic_write(path: str, text: str) -> None:
    """Atomic write: temporary file in the same directory then ``os.replace``."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    handle_fd, tmp_path = tempfile.mkstemp(prefix=".orvyren-chain-", suffix=".tmp",
                                           dir=directory)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _check_identifier(value: Any, kind: str) -> str:
    """Non-empty plain identifier (``[A-Za-z0-9._-]``) or contract error."""
    if not isinstance(value, str) or not value.strip():
        raise ChainContractError("{} is required (never empty)".format(kind))
    cleaned = value.strip()
    if cleaned in _ID_SEPARATORS or any(
            not (ch.isalnum() or ch in "._-") for ch in cleaned):
        raise ChainContractError(
            "{} must be a plain identifier ([A-Za-z0-9._-]): {!r}".format(kind, value))
    return cleaned


def _check_token(value: Any, kind: str) -> str:
    """Non-empty flat token (stage / event name) or contract error."""
    if not isinstance(value, str) or not value.strip():
        raise ChainContractError("{} is required (never empty)".format(kind))
    cleaned = value.strip()
    if any(ch in cleaned for ch in ("/", "\\", "\0")) or cleaned in (".", ".."):
        raise ChainContractError(
            "{} must be a flat token without path separators: {!r}".format(kind, value))
    return cleaned


def _check_artifact_name(value: Any) -> str:
    """Artifact names are plain file names inside ``root_dir/<stage>/``."""
    cleaned = _check_token(value, "artifact name")
    if os.path.basename(cleaned) != cleaned:
        raise ChainContractError(
            "artifact name must be a plain file name: {!r}".format(value))
    return cleaned


def new_run_id(prefix: str = "run") -> str:
    """Unique, readable, never-reused run identifier.

    ``<prefix>-<UTC timestamp>-<hex>`` — e.g.
    ``run-20261018T120102123456Z-3f9a2b1c4d5e``. The UTC timestamp makes the
    identifier sortable and readable, the cryptographic hex makes it unique;
    identifiers are never recycled (a re-run gets a new one plus
    ``parent_run_id``).
    """
    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")
    cleaned = _check_identifier(prefix, "prefix")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z"
    return "{}-{}-{}".format(cleaned, stamp, secrets.token_hex(6))


# --------------------------------------------------------------------------
# The run chain.
# --------------------------------------------------------------------------
class RunChain:
    """Shared run chain for one ``run_id``: hashed events + hashed artifacts.

    ``root_dir`` holds ``events.jsonl`` (append-only, hash-chained), the
    ``manifest.json`` artifact contract and the ``<stage>/<name>`` artifacts.
    Constructing a :class:`RunChain` on an existing ``root_dir`` **loads** the
    chain: a broken event chain or an identity mismatch is a
    :class:`ChainContractError` (fail-closed), never a silent restart.
    """

    def __init__(self, run_id: str, case_id: str, *, parent_run_id: str = "",
                 root_dir: str):
        self.run_id = _check_identifier(run_id, "run_id")
        self.parent_run_id = _check_identifier(parent_run_id, "parent_run_id") \
            if parent_run_id else ""
        if self.parent_run_id and self.parent_run_id == self.run_id:
            raise ChainContractError(
                "parent_run_id must differ from run_id (identifiers are never reused)")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ChainContractError("case_id is required (never empty)")
        if not isinstance(root_dir, str) or not root_dir.strip():
            raise ChainContractError("root_dir is required (never empty)")
        self.case_id = case_id.strip()
        self.root_dir = root_dir
        self.events_path = os.path.join(self.root_dir, "events.jsonl")
        self.manifest_path = os.path.join(self.root_dir, "manifest.json")
        self._artifacts: Dict[str, Dict[str, Any]] = {}
        self._head = GENESIS_HASH
        self._seq = 0
        os.makedirs(self.root_dir, exist_ok=True)
        self._load()

    # -- loading -----------------------------------------------------------
    def _load(self) -> None:
        self._load_events()
        self._load_manifest()

    def _load_events(self) -> None:
        if not os.path.exists(self.events_path):
            return
        previous = GENESIS_HASH
        count = 0
        try:
            with open(self.events_path, "r", encoding="utf-8") as handle:
                for index, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError as exc:
                        raise ChainContractError(
                            "events: line {}: invalid JSON".format(index)) from exc
                    if not isinstance(event, dict):
                        raise ChainContractError(
                            "events: line {}: object expected".format(index))
                    if event.get("run_id") != self.run_id:
                        raise ChainContractError(
                            "events: line {}: run_id mismatch".format(index))
                    if event.get("seq") != count + 1:
                        raise ChainContractError(
                            "events: line {}: unexpected seq {!r}".format(index, event.get("seq")))
                    if event.get("prev_hash") != previous:
                        raise ChainContractError(
                            "events: line {}: broken prev_hash".format(index))
                    if event.get("event_hash") != _event_hash(event):
                        raise ChainContractError(
                            "events: line {}: non-conforming event_hash".format(index))
                    previous = event["event_hash"]
                    count += 1
        except OSError as exc:
            raise ChainContractError("events: unreadable ({})".format(exc)) from exc
        self._head = previous
        self._seq = count

    def _load_manifest(self) -> None:
        if not os.path.exists(self.manifest_path):
            return
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, ValueError) as exc:
            raise ChainContractError("manifest: unreadable ({})".format(exc)) from exc
        if not isinstance(manifest, dict):
            raise ChainContractError("manifest: object expected")
        if manifest.get("schema_version") != SCHEMA_MANIFEST:
            raise ChainContractError("manifest: unexpected schema_version {!r}".format(
                manifest.get("schema_version")))
        if manifest.get("run_id") != self.run_id:
            raise ChainContractError("manifest: run_id mismatch ({!r})".format(
                manifest.get("run_id")))
        if manifest.get("case_id") != self.case_id:
            raise ChainContractError("manifest: case_id mismatch ({!r})".format(
                manifest.get("case_id")))
        if (manifest.get("parent_run_id") or "") != self.parent_run_id:
            raise ChainContractError("manifest: parent_run_id mismatch ({!r})".format(
                manifest.get("parent_run_id")))
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ChainContractError("manifest: artifacts object expected")
        for name, entry in artifacts.items():
            _check_artifact_name(name)
            if not isinstance(entry, dict):
                raise ChainContractError("manifest: artifact {} entry expected".format(name))
            if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
                raise ChainContractError("manifest: artifact {} invalid sha256".format(name))
            if not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
                raise ChainContractError("manifest: artifact {} invalid bytes".format(name))
            if not isinstance(entry.get("stage"), str) or not entry["stage"]:
                raise ChainContractError("manifest: artifact {} invalid stage".format(name))
            self._artifacts[str(name)] = {
                "stage": entry["stage"], "sha256": entry["sha256"],
                "bytes": entry["bytes"]}

    # -- persistence -------------------------------------------------------
    def manifest(self) -> Dict[str, Any]:
        """The artifact contract document (also written to ``manifest.json``)."""
        return {
            "schema_version": SCHEMA_MANIFEST,
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "case_id": self.case_id,
            "artifacts": {name: dict(self._artifacts[name]) for name in sorted(self._artifacts)},
            "events_head": self._head,
        }

    def _write_manifest(self) -> None:
        try:
            _atomic_write(self.manifest_path, _canonical_json(self.manifest()) + "\n")
        except OSError as exc:
            raise ChainContractError(
                "manifest: cannot write ({})".format(exc)) from exc

    # -- events ------------------------------------------------------------
    def record(self, stage: str, event: str, payload: Mapping) -> dict:
        """Append one event line to ``events.jsonl`` and return the line.

        The line carries ``run_id`` / ``parent_run_id`` / ``case_id`` / ``seq``
        / ``stage`` / ``event`` / ``ts_utc`` / ``payload`` / ``prev_hash`` /
        ``event_hash``. ``ts_utc`` is the single signed time field: payloads
        must be wall-clock free so the hashed content is reproducible.
        """
        stage_name = _check_token(stage, "stage")
        event_name = _check_token(event, "event")
        if not isinstance(payload, Mapping):
            raise ChainContractError("payload must be a mapping")
        line = {
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "case_id": self.case_id,
            "seq": self._seq + 1,
            "stage": stage_name,
            "event": event_name,
            "ts_utc": _utc_stamp(),
            "payload": dict(payload),
            "prev_hash": self._head,
        }
        line["event_hash"] = _event_hash(line)
        try:
            with open(self.events_path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(line) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ChainContractError(
                "events: cannot append ({})".format(exc)) from exc
        self._seq += 1
        self._head = line["event_hash"]
        self._write_manifest()
        return dict(line)

    # -- artifacts ---------------------------------------------------------
    def write_artifact(self, stage: str, name: str, payload: Any) -> str:
        """Write ``root_dir/<stage>/<name>`` (canonical JSON) and return its sha256.

        The file carries its provenance envelope (``run_id``, ``parent_run_id``,
        ``case_id``, ``stage``, ``name``) around the payload — no wall-clock,
        so equal payloads under equal identity hash equally. The manifest
        entry ``{stage, sha256, bytes}`` is updated atomically; an artifact
        name is **immutable** (same name, different content = contract error).
        """
        stage_name = _check_token(stage, "stage")
        artifact_name = _check_artifact_name(name)
        envelope = {
            "schema": SCHEMA_ARTIFACT,
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "case_id": self.case_id,
            "stage": stage_name,
            "name": artifact_name,
            "payload": payload,
        }
        text = _canonical_json(envelope) + "\n"
        data = text.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        entry = {"stage": stage_name, "sha256": digest, "bytes": len(data)}
        existing = self._artifacts.get(artifact_name)
        if existing is not None and existing["sha256"] != digest:
            raise ChainContractError(
                "artifact {} already written with a different sha256 "
                "(artifacts are immutable)".format(artifact_name))
        try:
            _atomic_write(os.path.join(self.root_dir, stage_name, artifact_name), text)
        except OSError as exc:
            raise ChainContractError(
                "artifact {}: cannot write ({})".format(artifact_name, exc)) from exc
        self._artifacts[artifact_name] = entry
        self._write_manifest()
        return digest

    def _artifact_bytes(self, name: str, entry: Mapping[str, Any]) -> bytes:
        path = os.path.join(self.root_dir, str(entry.get("stage") or ""), name)
        try:
            with open(path, "rb") as handle:
                return handle.read()
        except OSError as exc:
            raise ChainContractError(
                "artifact {}: unreadable ({})".format(name, exc)) from exc

    # -- handoffs ----------------------------------------------------------
    def handoff(self, stage_from: str, stage_to: str,
                artifact_names: Sequence[str]) -> dict:
        """Verify the named artifacts before crossing ``stage_from -> stage_to``.

        Every name must exist in the manifest with a valid sha256 — anything
        else raises :class:`ChainContractError` (fail-closed). Pure
        verification: the transition itself is journaled by :meth:`record`.
        """
        source = _check_token(stage_from, "stage_from")
        target = _check_token(stage_to, "stage_to")
        if isinstance(artifact_names, (str, bytes)) or not isinstance(artifact_names, Sequence):
            raise ChainContractError("artifact_names must be a sequence of names")
        verified: Dict[str, Dict[str, Any]] = {}
        for name in artifact_names:
            artifact_name = _check_artifact_name(name)
            entry = self._artifacts.get(artifact_name)
            if entry is None:
                raise ChainContractError(
                    "handoff {}->{}: artifact {} not in the manifest".format(
                        source, target, artifact_name))
            data = self._artifact_bytes(artifact_name, entry)
            if hashlib.sha256(data).hexdigest() != entry["sha256"] \
                    or len(data) != entry["bytes"]:
                raise ChainContractError(
                    "handoff {}->{}: artifact {} sha256 mismatch (contract "
                    "violation)".format(source, target, artifact_name))
            verified[artifact_name] = dict(entry)
        return {
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "case_id": self.case_id,
            "stage_from": source,
            "stage_to": target,
            "artifacts": verified,
            "ok": True,
        }

    # -- verification ------------------------------------------------------
    def verify(self) -> Tuple[bool, str]:
        """Recompute the event chain and the sha256 of every manifest artifact.

        Returns ``(True, "")`` when the whole chain verifies, else
        ``(False, detail)`` — the detail never contains a payload value.
        """
        previous = GENESIS_HASH
        count = 0
        if os.path.exists(self.events_path):
            try:
                with open(self.events_path, "r", encoding="utf-8") as handle:
                    for index, line in enumerate(handle, start=1):
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except ValueError:
                            return False, "events: line {}: invalid JSON".format(index)
                        if not isinstance(event, dict):
                            return False, "events: line {}: object expected".format(index)
                        if event.get("run_id") != self.run_id:
                            return False, "events: line {}: run_id mismatch".format(index)
                        if event.get("seq") != count + 1:
                            return False, "events: line {}: unexpected seq".format(index)
                        if event.get("prev_hash") != previous:
                            return False, "events: line {}: broken prev_hash".format(index)
                        if event.get("event_hash") != _event_hash(event):
                            return False, "events: line {}: non-conforming event_hash".format(index)
                        previous = event["event_hash"]
                        count += 1
            except OSError as exc:
                return False, "events: unreadable ({})".format(exc)
        if previous != self._head or count != self._seq:
            return False, "events: chain head out of sync (reloaded state required)"
        for name in sorted(self._artifacts):
            entry = self._artifacts[name]
            try:
                data = self._artifact_bytes(name, entry)
            except ChainContractError as exc:
                return False, str(exc)
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                return False, "artifact {}: sha256 mismatch".format(name)
            if len(data) != entry["bytes"]:
                return False, "artifact {}: size mismatch".format(name)
        if not os.path.exists(self.manifest_path) and self._artifacts:
            return False, "manifest: missing while artifacts are declared"
        return True, ""
