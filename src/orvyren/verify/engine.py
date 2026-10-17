#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — T10 third-party verifier engine (W6 lots L6.1-L6.4).

Spec: B6_AUDIT_ETUDE.md §1-§2. Stdlib-only, offline by default. The engine is
ONE self-contained file so the audit packet can ship a frozen copy
(`verify/_orvyren/verify_engine.py`) that runs without the producer
repository: the dossier builder and the policy service are taken from
``orvyren`` when present (repository mode) and from the sibling frozen copies
otherwise (packet mode, see the shim below).

Classes of verifiability (B6 §2.2, never mixed):
  A — recomputable bit-for-bit offline (hash chains, dossier self-hash and
      re-rendering, policy verdicts, graph snapshot, fixture-derived signals,
      intent <-> receipt crossing);
  B — re-verified (on-chain facts, only under ``--rpc``);
  C — not replayable, covered by the journal (agent/LLM stream).

Honesty rules: a control never claims more than its class; missing or invalid
pieces are named in the report, never raised as exceptions; the report is
deterministic (same target => same verdicts; ``generated_at_utc`` excluded).
Exit codes: 0 all green, 1 integrity failure, 2 usage, 3 network unavailable
in --rpc mode (A controls are still rendered).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERIFIER_VERSION = "T10/v1"
VERIFIER_NAME = "orvyren.verify"
GENESIS = "0" * 64
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEFAULT_DECIMALS = 6

# --- repository-or-frozen code (double distribution, B6 §1.5/§2.8) ----------
try:  # repository mode
    from orvyren.audit import dossier as _dossier_mod  # type: ignore
    from orvyren import policy as _policy_mod  # type: ignore
    _FROZEN_MODE = False
except ModuleNotFoundError:  # frozen packet mode
    from . import audit_dossier as _dossier_mod  # type: ignore  # noqa: F401
    from . import policy as _policy_mod  # type: ignore  # noqa: F401
    _FROZEN_MODE = True


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, lf_normalize: bool = False) -> Optional[str]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if lf_normalize:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: str) -> List[Any]:
    out: List[Any] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    out.append({"__unparsable__": line[:200]})
    except OSError:
        return []
    return out


def load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: Any) -> Optional[dt.datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    return moment


def new_check(check_id: str, cls: str, ok: bool, detail: Dict[str, Any],
              status: Optional[str] = None) -> Dict[str, Any]:
    if status is None:
        status = {"A": "RECOMPUTED", "B": "REVERIFIED", "C": "COVERED"}[cls]
    return {"id": check_id, "class": cls, "status": status, "ok": bool(ok),
            "detail": detail}


# --------------------------------------------------------------------------- #
# Target resolution and manifest
# --------------------------------------------------------------------------- #

def resolve_target(target: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (root_dir, cleanup_dir, error). A zip is extracted to a temp dir."""
    if not target:
        return None, None, "usage: empty target"
    path = os.path.abspath(target)
    if os.path.isdir(path):
        return path, None, None
    if os.path.isfile(path) and path.lower().endswith(".zip"):
        temp = tempfile.mkdtemp(prefix="orvyren_verify_")
        try:
            with zipfile.ZipFile(path) as archive:
                _extract_zip_safely(archive, temp)
        except (zipfile.BadZipFile, OSError) as exc:
            shutil.rmtree(temp, ignore_errors=True)
            return None, None, "unreadable zip: %s" % exc
        entries = [name for name in os.listdir(temp)
                   if os.path.isdir(os.path.join(temp, name))]
        if len(entries) == 1:
            return os.path.join(temp, entries[0]), temp, None
        return temp, temp, None
    return None, None, "target must be an audit packet zip or directory: %s" % target


def packet_files(root: str) -> List[str]:
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != "__pycache__"]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            files.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(files)


def safe_join(root: str, rel: Any) -> Optional[str]:
    """Join a manifest-relative path without allowing escape from ``root``.

    Audit packets are untrusted input. Every path read from the manifest,
    HASHES.txt or HASHES table must stay inside the extracted packet root;
    ``../``, absolute paths and drive-qualified paths are rejected.
    """
    if not isinstance(rel, str) or not rel.strip():
        return None
    normalized = rel.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return None
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    root_abs = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_abs, *parts))
    try:
        if os.path.commonpath((root_abs, candidate)) != root_abs:
            return None
    except ValueError:
        return None
    return candidate


def _safe_load_json(root: str, rel: Any) -> Any:
    path = safe_join(root, rel)
    return load_json(path) if path else None


def _safe_read_jsonl(root: str, rel: Any) -> List[Any]:
    path = safe_join(root, rel)
    return read_jsonl(path) if path else []


def _safe_sha256_file(root: str, rel: Any, *, lf_normalize: bool = False) -> Optional[str]:
    path = safe_join(root, rel)
    return sha256_file(path, lf_normalize=lf_normalize) if path else None


def _extract_zip_safely(archive: zipfile.ZipFile, destination: str) -> None:
    """Extract a packet zip while refusing zip-slip, symlinks and zip bombs."""
    max_bytes = 512 * 1024 * 1024
    total_bytes = 0
    root_abs = os.path.abspath(destination)
    for member in archive.infolist():
        name = member.filename
        target = safe_join(root_abs, name)
        if target is None:
            raise zipfile.BadZipFile("unsafe archive member: %s" % name)
        total_bytes += int(member.file_size)
        if total_bytes > max_bytes:
            raise zipfile.BadZipFile("archive expands beyond the 512 MiB safety limit")
        mode = (member.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise zipfile.BadZipFile("symlink archive member refused: %s" % name)
        if member.is_dir():
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with archive.open(member, "r") as source, open(target, "wb") as output:
            shutil.copyfileobj(source, output)


# --------------------------------------------------------------------------- #
# A1 — hash chains of the streams (+ LINK/SEAL junction)
# --------------------------------------------------------------------------- #

def _chain_state(records: Sequence[Any]) -> Dict[str, Any]:
    """Recompute the SHA-256 chain of one stream; first divergence named."""
    prev = GENESIS
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or "__unparsable__" in record:
            return {"ok": False, "first_bad": index,
                    "reason": "unparsable JSONL line at position %d" % index}
        body = {key: value for key, value in record.items() if key != "record_hash"}
        recomputed = sha256_hex(canonical_json(body).encode("utf-8"))
        if recomputed != record.get("record_hash"):
            return {"ok": False, "first_bad": index, "reason": "record_hash mismatch",
                    "expected": record.get("record_hash"), "computed": recomputed}
        if record.get("prev_hash") != prev:
            return {"ok": False, "first_bad": index, "reason": "prev_hash break",
                    "expected_prev": prev, "found": record.get("prev_hash")}
        prev = recomputed
    return {"ok": True, "head": prev, "records": len(records)}


def check_a1_chains(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    streams = manifest.get("streams") or {}
    for stream_id in ("exec", "agent", "graph"):
        decl = streams.get(stream_id) or {}
        if not decl.get("present"):
            checks.append(new_check(
                "A1.%s.absent" % stream_id, "C", True,
                {"declared_absent": True, "reason": decl.get("reason", "")},
                status="COVERED"))
            continue
        path = safe_join(root, decl.get("path", ""))
        records = read_jsonl(path) if path else []
        state = _chain_state(records)
        expected_count = decl.get("records")
        expected_head = decl.get("head_hash")
        detail: Dict[str, Any] = {"path": decl.get("path"), "records": len(records),
                                  "head_computed": state.get("head"),
                                  "head_expected": expected_head}
        ok = bool(state.get("ok"))
        if path is None:
            ok = False
            detail["reason"] = "unsafe or missing stream path"
        if not ok:
            detail["first_bad"] = state.get("first_bad")
            detail["reason"] = state.get("reason") or detail.get("reason")
        tail_note = None
        if ok and stream_id == "exec":
            if not isinstance(expected_count, int):
                # Without the manifest-time count the LINK/SEAL junction cannot be
                # located: never pass silently on the chain alone (B6 §1.4).
                ok = False
                detail["reason"] = ("exec stream declared without an integer "
                                    "records count: LINK/SEAL junction not verifiable")
            else:
                # B6 §1.4: after the manifest-time head, exec carries 3 LINK + 1 SEAL.
                head_at = _chain_state(records[:expected_count])
                if not head_at.get("ok") or head_at.get("head") != expected_head:
                    ok = False
                    detail["reason"] = "head before LINK/SEAL does not match the manifest"
                    detail["head_at_%d" % expected_count] = head_at.get("head")
                tail = records[expected_count:]
                kinds = [record.get("kind") for record in tail if isinstance(record, dict)]
                if kinds != ["LINK", "LINK", "LINK", "SEAL"]:
                    ok = False
                    detail["tail_kinds"] = kinds
                    detail["reason"] = detail.get("reason") or "tail must be 3 LINK + 1 SEAL"
                else:
                    seal = tail[-1]
                    with open(os.path.join(root, "manifest.json"), "rb") as handle:
                        manifest_bytes = handle.read()
                    seal_expected = sha256_hex(manifest_bytes)
                    seal_found = (seal.get("payload") or {}).get("manifest_sha256")
                    links = {link.get("payload", {}).get("stream"): link.get("payload", {})
                             for link in tail[:3]}
                    graph_head = (streams.get("graph") or {}).get("head_hash")
                    link_ok = (links.get("graph", {}).get("head_hash") == graph_head
                               and links.get("decision", {}).get("sha256")
                               == (manifest.get("decision") or {}).get("sha256"))
                    tail_note = {"seal_ok": seal_found == seal_expected, "links_ok": link_ok}
                    if seal_found != seal_expected or not link_ok:
                        ok = False
                        detail["reason"] = detail.get("reason") or "LINK/SEAL junction mismatch"
        if ok and stream_id in ("graph", "agent"):
            # The manifest-declared head is part of the contract for these
            # streams: a stream rewritten end-to-end (recomputed per-record
            # hashes, same length) must still fail on the head (B6 §2.4 A1).
            if isinstance(expected_count, int) and len(records) != expected_count:
                ok = False
                detail["reason"] = "%s records count mismatch" % stream_id
            if state.get("head") != expected_head:
                ok = False
                detail["reason"] = detail.get("reason") or (
                    "%s head_hash does not match the manifest" % stream_id)
        if tail_note:
            detail.update(tail_note)
        checks.append(new_check("A1.%s.chain" % stream_id, "A", ok, detail))
    return checks


# --------------------------------------------------------------------------- #
# A2 — dossier self-hash (B6 §2.4 A2)
# --------------------------------------------------------------------------- #

_MD_SELF_RE = re.compile(r"dossier \(self, md\)[^\n]*`([0-9a-f]{64})`")
_HTML_SELF_RE = re.compile(r"dossier \(self, html\).{0,200}?<code>([0-9a-f]{64})</code>",
                           re.DOTALL)


def recompute_self_hash(path: str, pattern: re.Pattern) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        return {"ok": False, "reason": "unreadable: %s" % exc}
    match = pattern.search(text)
    if not match:
        return {"ok": False, "reason": "self-hash row not found"}
    declared = match.group(1)
    # Zero the self field **at its own position** (the matched row): the hash may
    # legitimately appear earlier in the file (input table, embedded data) and a
    # first-occurrence substitution would then zero the wrong place (the producer
    # stamps the field positionally too — audit/dossier.py:_stamp_self_hash).
    zeroed = text[:match.start(1)] + GENESIS + text[match.end(1):]
    computed = sha256_hex(zeroed.encode("utf-8"))
    return {"ok": declared == computed, "declared": declared, "computed": computed}


def check_a2_dossier(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    dossier = manifest.get("dossier") or {}
    for label, key, pattern in (("md", "md", _MD_SELF_RE), ("html", "html", _HTML_SELF_RE)):
        rel = dossier.get(key)
        if not rel:
            checks.append(new_check("A2.dossier.%s" % label, "A", False,
                                    {"missing": "dossier.%s not declared in the manifest" % key}))
            continue
        detail = {"path": rel}
        safe_path = safe_join(root, rel)
        if safe_path is None:
            detail.update({"ok": False, "reason": "unsafe dossier path"})
        else:
            detail.update(recompute_self_hash(safe_path, pattern))
        checks.append(new_check("A2.dossier.%s" % label, "A", bool(detail.get("ok")), detail))
    return checks


# --------------------------------------------------------------------------- #
# A3 — HASHES.txt coverage + dossier input table (B6 §2.4 A3)
# --------------------------------------------------------------------------- #

def check_a3_hashes(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    hashes_path = os.path.join(root, "HASHES.txt")
    if not os.path.isfile(hashes_path):
        return [new_check("A3.packet.sha256", "A", False,
                          {"missing": "HASHES.txt"})]
    listed: Dict[str, str] = {}
    bundle_digest_expected = None
    try:
        with open(hashes_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                if line.startswith("bundle_digest"):
                    # legacy layout (digest line inside HASHES.txt)
                    bundle_digest_expected = line.split()[-1]
                    continue
                match = re.match(r"^([0-9a-f]{64})  (.+)$", line)
                if match:
                    listed[match.group(2)] = match.group(1)
    except OSError as exc:
        return [new_check("A3.packet.sha256", "A", False, {"unreadable": str(exc)})]
    bundle_file = os.path.join(root, "BUNDLE_DIGEST.txt")
    if os.path.isfile(bundle_file):
        try:
            with open(bundle_file, "r", encoding="utf-8") as handle:
                for token in handle.read().split():
                    if re.match(r"^[0-9a-f]{64}$", token):
                        bundle_digest_expected = token
                        break
        except OSError:
            pass

    missing_files: List[str] = []
    mismatches: List[Dict[str, str]] = []
    for rel, digest in sorted(listed.items()):
        actual = _safe_sha256_file(root, rel)
        if actual is None:
            missing_files.append(rel)
        elif actual != digest:
            mismatches.append({"path": rel, "declared": digest, "actual": actual})
    present = [rel for rel in packet_files(root) if rel != "HASHES.txt"]
    unlisted = sorted(set(present) - set(listed))
    detail = {"listed": len(listed), "missing_listed_files": missing_files,
              "mismatches": mismatches, "unlisted_files": unlisted}
    digest_input = sorted([rel, digest] for rel, digest in listed.items()
                          if rel != "BUNDLE_DIGEST.txt"
                          and not (rel.startswith("dossier_")
                                  and (rel.endswith(".md") or rel.endswith(".html"))))
    bundle_digest_computed = sha256_hex(canonical_json(digest_input).encode("utf-8"))
    detail["bundle_digest_expected"] = bundle_digest_expected
    detail["bundle_digest_computed"] = bundle_digest_computed
    ok = (not missing_files and not mismatches and not unlisted
          and bundle_digest_expected == bundle_digest_computed)
    checks.append(new_check("A3.packet.sha256", "A", ok, detail))

    # dossier input table: each declared SHA-256 must match the packet file
    dossier = manifest.get("dossier") or {}
    md_rel = dossier.get("md")
    if md_rel:
        md_path = safe_join(root, md_rel)
        try:
            with open(md_path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, TypeError):
            text = ""
        table_problems: List[Dict[str, str]] = []
        table_checked = 0
        for match in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*`([0-9a-f]{64})`\s*\|$",
                                 text, re.MULTILINE):
            label, path, digest = match.group(1).strip(), match.group(2).strip(), match.group(3)
            if "self" in label:
                continue
            actual = _safe_sha256_file(root, path, lf_normalize=True)
            table_checked += 1
            if actual != digest:
                table_problems.append({"label": label, "path": path,
                                       "declared": digest, "actual": actual})
        checks.append(new_check("A3.dossier.inputs", "A", not table_problems,
                                {"rows_checked": table_checked, "problems": table_problems}))
    else:
        checks.append(new_check("A3.dossier.inputs", "A", False,
                                {"missing": "dossier.md not declared"}))
    return checks


# --------------------------------------------------------------------------- #
# A4 — dossier re-rendering, byte-for-byte (B6 §2.4 A4)
# --------------------------------------------------------------------------- #

def check_a4_rerender(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    dossier = manifest.get("dossier") or {}
    decl = dossier.get("inputs") or {}
    decision_rel = decl.get("decision")
    extras = decl.get("extras") or {}
    generated_at = dossier.get("generated_at")
    if not decision_rel or not generated_at:
        return [new_check("A4.dossier.rerender", "A", False,
                          {"missing": "manifest.dossier.inputs.decision / generated_at"})]
    import tempfile as _tempfile
    out_dir = _tempfile.mkdtemp(prefix="orvyren_a4_")
    staging = _tempfile.mkdtemp(prefix="orvyren_a4_in_")
    # The staging display root is module-global state: save it and restore it in
    # the finally block, or every later dossier build in this process (other
    # tests, other packets) resolves its displayed paths against a dead staging.
    had_repo_root = hasattr(_dossier_mod, "_REPO_ROOT")
    previous_repo_root = getattr(_dossier_mod, "_REPO_ROOT", None)
    try:
        # The producer built the packet dossier with the packet root as both
        # its display root and its output directory. Reproduce both: stage the
        # inputs under a fresh root and render there, so every displayed path
        # (the self row included) is identical.
        def _stage(rel: str) -> str:
            source = safe_join(root, rel)
            if source is None:
                raise ValueError("unsafe dossier input path: %s" % rel)
            target = safe_join(staging, rel)
            if target is None:
                raise ValueError("unsafe staging path: %s" % rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
            return target

        try:
            decision_staged = _stage(decision_rel)
            extra_paths = {label: _stage(rel) for label, rel in sorted(extras.items())}
        except (OSError, ValueError) as exc:
            return [new_check("A4.dossier.rerender", "A", False,
                              {"reason": "unsafe or missing dossier input: %s" % exc})]
        _dossier_mod._REPO_ROOT = staging
        built = _dossier_mod.build(decision_staged, staging,
                                   extra_paths=extra_paths, generated_at=generated_at)
        results: List[Dict[str, Any]] = []
        pairs = (("md", built["md_path"], dossier.get("md", "")),
                 ("html", built["html_path"], dossier.get("html", "")))
        for label, rebuilt_path, packet_rel in pairs:
            problems: List[str] = []
            if not packet_rel:
                problems.append("packet dossier.%s not declared" % label)
            else:
                with open(rebuilt_path, "rb") as handle:
                    rebuilt = handle.read()
                packet_path = safe_join(root, packet_rel)
                try:
                    if packet_path is None:
                        raise OSError("unsafe packet path")
                    with open(packet_path, "rb") as handle:
                        original = handle.read()
                except OSError:
                    original = None
                if original is None:
                    problems.append("packet file missing: %s" % packet_rel)
                elif rebuilt != original:
                    first_diff = next((i for i, (a, b) in enumerate(zip(rebuilt, original))
                                       if a != b), min(len(rebuilt), len(original)))
                    problems.append("byte mismatch at offset %d (rebuilt %d bytes, packet %d bytes)"
                                    % (first_diff, len(rebuilt), len(original)))
            results.append(new_check("A4.dossier.rerender.%s" % label, "A",
                                     not problems,
                                     {"problems": problems, "generated_at": generated_at}))
        return results
    finally:
        if had_repo_root:
            _dossier_mod._REPO_ROOT = previous_repo_root
        elif hasattr(_dossier_mod, "_REPO_ROOT"):
            del _dossier_mod._REPO_ROOT
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)


# --------------------------------------------------------------------------- #
# A5 — policy verdicts recomputed (B6 §2.4 A5)
# --------------------------------------------------------------------------- #

def _resolve_recipients(root: str, policy_data: Dict[str, Any], intents: List[Dict[str, Any]]):
    for key in ("recipients_resolved", "recipient_addresses", "wallets"):
        value = policy_data.get(key)
        if isinstance(value, dict) and value:
            return set(str(item).lower() for item in value.values()), key
        if isinstance(value, list) and value:
            return set(str(item).lower() for item in value), key
    registry = load_json(os.path.join(root, "policy", "intent_registry.json"))
    if isinstance(registry, dict):
        recipients = registry.get("recipients") or registry.get("recipient_addresses")
        if isinstance(recipients, (dict, list)) and recipients:
            values = recipients.values() if isinstance(recipients, dict) else recipients
            return set(str(item).lower() for item in values), "intent_registry.json"
    # fallback: the recorded (masked) recipient strings themselves — string
    # equality on the masked form still discriminates distinct addresses
    masked = {str((entry.get("payload") or {}).get("recipient", "")).lower()
              for entry in intents if (entry.get("payload") or {}).get("recipient")}
    return masked, "recorded intents (masked recipients; documented fallback)"


def check_a5_policy(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    policy_rel = (manifest.get("policy") or {}).get("file", "policy/policy.effective.json")
    policy_data = _safe_load_json(root, policy_rel)
    if not isinstance(policy_data, dict):
        return [new_check("A5.policy.verdicts", "A", False,
                          {"missing": "unreadable %s" % policy_rel})]
    exec_decl = (manifest.get("streams") or {}).get("exec") or {}
    records = _safe_read_jsonl(root, exec_decl.get("path", "audit.jsonl"))
    records = [record for record in records if isinstance(record, dict)]
    intents = [record for record in records if record.get("kind") == "INTENT"]
    policies = [record for record in records if record.get("kind") == "POLICY"]
    if not policies:
        return [new_check("A5.policy.verdicts", "A", False,
                          {"reason": "no POLICY records in the journal"})]

    allowed_recipients, source = _resolve_recipients(root, policy_data, intents)
    try:
        ttl_minutes = int(policy_data.get("ttl_intent_minutes", 15))
        ttl_hours = int(policy_data.get("permission_ttl_hours", 24))
        max_per_tx = float(policy_data.get("max_per_tx", 100.0))
        max_cumulative = float(policy_data.get("max_cumulative_24h", 300.0))
        chain_id = int(policy_data.get("chain_id", 0))
    except (TypeError, ValueError) as exc:
        # Honesty rule: an invalid policy field is named in the report, never
        # raised out of the verifier.
        return [new_check("A5.policy.verdicts", "A", False,
                          {"reason": "unreadable numeric field in %s: %s"
                                     % (policy_rel, exc)})]
    asset = str(policy_data.get("asset", ""))

    intents_by_id = {}
    for intent in intents:
        payload = intent.get("payload") or {}
        if payload.get("intent_id"):
            intents_by_id[payload["intent_id"]] = payload

    results: List[Dict[str, Any]] = []
    unresolvable: List[Dict[str, Any]] = []
    seen: List[str] = []
    rolling_amount = 0.0
    for record in policies:
        payload = record.get("payload") or {}
        intent_id = payload.get("intent_id")
        intent = intents_by_id.get(intent_id)
        if intent is None:
            unresolvable.append({
                "intent_id": intent_id,
                "run": (record.get("refs") or {}).get("run"),
                "verdict": payload.get("verdict"),
                "reason": "INTENT record not journaled (kit v1 run-B offline-denial "
                          "path) — declared, not recomputable from the packet"})
            continue
        expiry = parse_iso(intent.get("expiry"))
        moment = parse_iso(payload.get("decided_at")) or expiry
        created_at = (expiry - dt.timedelta(minutes=ttl_minutes)) if expiry else moment
        context = payload.get("context_used") or {}
        try:
            cumulative = float(context.get("cumulative_spent", rolling_amount))
        except (TypeError, ValueError) as exc:
            results.append({"intent_id": intent_id, "ok": False,
                            "reason": "unreadable context_used.cumulative_spent: %s" % exc})
            continue
        if moment is None:
            results.append({"intent_id": intent_id, "ok": False,
                            "reason": "missing decided_at/expiry: policy clock cannot be recomputed"})
            continue
        try:
            assert created_at is not None
            intent_obj = _policy_mod.Intent(
                intent_id=str(intent_id), action=str(intent.get("action", "transfer")),
                chain_id=chain_id, asset=str(intent.get("asset", asset)),
                amount=float(intent.get("amount", 0.0)),
                recipient=str(intent.get("recipient", "")),
                created_at=created_at, justification="")
            config = _policy_mod.PolicyConfig(
                allowed_chain_ids=frozenset({chain_id}),
                allowed_assets=frozenset({asset.lower()}),
                allowed_recipients=frozenset(allowed_recipients),
                max_per_tx=max_per_tx, max_cumulative=max_cumulative,
                permission_expires_at=(moment + dt.timedelta(hours=ttl_hours)) if moment else None)
            decision = _policy_mod.evaluate(intent_obj, config, now=moment,
                                            seen_intent_ids=tuple(seen),
                                            cumulative_spent=cumulative)
        except Exception as exc:  # noqa: BLE001 - never abort the report
            results.append({"intent_id": intent_id, "ok": False,
                            "reason": "evaluate() raised %s" % exc})
            continue
        recorded_verdict = payload.get("verdict")
        recorded_reasons = sorted(payload.get("reasons") or [])
        recomputed_reasons = sorted(decision.reasons or [])
        ok = (recorded_verdict == decision.verdict
              and recorded_reasons == recomputed_reasons)
        results.append({
            "intent_id": intent_id, "ok": ok,
            "recorded": {"verdict": recorded_verdict, "reasons": recorded_reasons},
            "recomputed": {"verdict": decision.verdict, "reasons": recomputed_reasons},
        })
        seen.append(str(intent_id))
        if recorded_verdict == "ALLOW":
            rolling_amount += float(intent.get("amount", 0.0))

    failures = [entry for entry in results if not entry.get("ok")]
    return [new_check("A5.policy.verdicts", "A", not failures,
                      {"intents_recomputed": len(results), "failures": failures,
                       "policy_records_without_intent": unresolvable,
                       "recipients_source": source})]


# --------------------------------------------------------------------------- #
# A6 — graph snapshot hash (B6 §2.4 A6)
# --------------------------------------------------------------------------- #

def snapshot_hash(payload: Dict[str, Any]) -> str:
    frozen = {key: value for key, value in payload.items() if key != "snapshot_hash"}
    return sha256_hex(canonical_json(frozen).encode("utf-8"))


def check_a6_snapshot(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    decl = ((manifest.get("streams") or {}).get("graph") or {}).get("snapshot") or {}
    rel = decl.get("path")
    if not rel:
        return [new_check("A6.graph.snapshot", "A", False,
                          {"missing": "manifest.streams.graph.snapshot.path"})]
    data = _safe_load_json(root, rel)
    if not isinstance(data, dict):
        return [new_check("A6.graph.snapshot", "A", False,
                          {"missing": "unreadable %s" % rel})]
    computed = snapshot_hash(data)
    declared = decl.get("snapshot_hash")
    embedded = data.get("snapshot_hash")
    ok = computed == declared == embedded
    return [new_check("A6.graph.snapshot", "A", ok,
                      {"path": rel, "declared": declared, "embedded": embedded,
                       "computed": computed, "records": (data.get("counts") or {}).get("records")})]


# --------------------------------------------------------------------------- #
# A7 — signals recomputed from the archived fixtures (B6 §2.4 A7)
# --------------------------------------------------------------------------- #

def _recompute_signals(corpus_path: str, window_start: str, window_end: str):
    import csv as _csv
    start = parse_iso(window_start)
    end = parse_iso(window_end)
    if start is None or end is None:
        raise ValueError("decision window missing or unparsable bounds (%r, %r)"
                         % (window_start, window_end))
    # independent venues only (the aggregator is not an independent venue)
    prices = {"bitstamp": "close_usd", "binance": "close_usdcusdt"}
    venue_hours: Dict[str, set] = {venue: set() for venue in prices}
    supply: List[Tuple[dt.datetime, float]] = []
    with open(corpus_path, "r", encoding="utf-8") as handle:
        for row in _csv.DictReader(handle):
            moment = parse_iso(row["timestamp_utc"])
            if moment is None or not (start <= moment <= end):
                continue
            value = float(row["value"])
            if row["venue"] == "defillama_supply_aggregate" and row["metric"] == "circulating_usd":
                supply.append((moment, value))
            elif row["venue"] in prices and row["metric"] == prices[row["venue"]]:
                if value < 0.99:  # deviation > 1% below peg
                    venue_hours[row["venue"]].add(moment)
    supply.sort()
    max_drop = None
    for previous, current in zip(supply, supply[1:]):
        hours = (current[0] - previous[0]).total_seconds() / 3600.0
        if 0 < hours <= 24:
            if previous[1] == 0:
                raise ValueError("zero supply baseline at %s: percentage change "
                                 "undefined" % previous[0].isoformat())
            change = (current[1] - previous[1]) / previous[1] * 100.0
            max_drop = change if max_drop is None or change < max_drop else max_drop
    per_hour: Dict[Any, int] = {}
    for hours_set in venue_hours.values():
        for hour in hours_set:
            per_hour[hour] = per_hour.get(hour, 0) + 1
    simultaneous = sum(1 for count in per_hour.values() if count >= 2)
    return {"max_24h_supply_drop_pct": None if max_drop is None else round(max_drop, 6),
            "simultaneous_alert_hours": simultaneous}


def check_a7_fixtures(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    fixtures = manifest.get("fixtures") or {}
    corpus_rel = fixtures.get("corpus")
    decision_rel = (manifest.get("decision") or {}).get("path")
    if not corpus_rel or not decision_rel:
        return [new_check("A7.fixtures.signals", "A", False,
                          {"missing": "manifest.fixtures.corpus / manifest.decision.path"})]
    decision = _safe_load_json(root, decision_rel)
    if not isinstance(decision, dict):
        return [new_check("A7.fixtures.signals", "A", False,
                          {"missing": "unreadable %s" % decision_rel})]
    window = decision.get("window") or {}
    try:
        corpus_path = safe_join(root, corpus_rel)
        if corpus_path is None:
            raise ValueError("unsafe corpus path")
        recomputed = _recompute_signals(corpus_path,
                                        window.get("start"), window.get("end"))
    except (OSError, KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
        return [new_check("A7.fixtures.signals", "A", False,
                          {"reason": "recompute failed: %s" % exc})]
    h2 = ((decision.get("hypothesis_verdicts") or {}).get("H2")) or {}
    criteria_evaluated = h2.get("criteria_evaluated")
    first_criterion = (criteria_evaluated[0]
                       if isinstance(criteria_evaluated, list) and criteria_evaluated
                       else None)
    recorded_h2 = ((first_criterion.get("computed") or {})
                   if isinstance(first_criterion, dict) else {})
    comparisons = {
        "max_24h_supply_drop_pct": {
            "recorded": recorded_h2.get("max_24h_supply_drop_pct"),
            "recomputed": recomputed["max_24h_supply_drop_pct"]},
        "simultaneous_alert_hours": {
            "recorded": recorded_h2.get("simultaneous_alert_hours"),
            "recomputed": recomputed["simultaneous_alert_hours"]},
    }
    failures = {key: value for key, value in comparisons.items()
                if value["recorded"] != value["recomputed"]}
    return [new_check("A7.fixtures.signals", "A", not failures,
                      {"comparisons": comparisons, "failures": failures,
                       "corpus": corpus_rel})]


# --------------------------------------------------------------------------- #
# A8 — intent <-> receipt crossing (B6 §2.4 A8)
# --------------------------------------------------------------------------- #

def _topic_address(topic: str) -> str:
    return "0x" + topic[-40:]


def _masked_match(masked: str, address: str) -> bool:
    if not masked:
        return False
    text = masked.replace("\u2026", "...")
    if "..." in text:
        prefix, suffix = text.split("...", 1)
        return address.lower().startswith(prefix.lower()) and address.lower().endswith(suffix.lower())
    return masked.lower() == address.lower()


def check_a8_receipts(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    exec_decl = (manifest.get("streams") or {}).get("exec") or {}
    records = [record for record in _safe_read_jsonl(root, exec_decl.get("path", "audit.jsonl"))
               if isinstance(record, dict)]
    intents_by_id = {}
    for record in records:
        if record.get("kind") == "INTENT":
            payload = record.get("payload") or {}
            intents_by_id[payload.get("intent_id")] = payload
    checks: List[Dict[str, Any]] = []
    receipts = [record for record in records if record.get("kind") == "RECEIPT"]
    if not receipts:
        return [new_check("A8.receipts.cross", "A", False,
                          {"reason": "no RECEIPT records in the journal"})]
    problems: List[Dict[str, Any]] = []
    for record in receipts:
        payload = record.get("payload") or {}
        tx_hash = payload.get("tx_hash")
        raw_rel = payload.get("raw_ref")
        refs = record.get("refs") or {}
        intent = intents_by_id.get(refs.get("intent_id"))
        entry: Dict[str, Any] = {"tx_hash": tx_hash, "raw_ref": raw_rel}
        if not raw_rel:
            entry["reason"] = "raw_ref missing"
            problems.append(entry)
            continue
        raw_path = safe_join(root, raw_rel)
        actual_sha = sha256_file(raw_path) if raw_path else None
        if actual_sha is None:
            entry["reason"] = "raw receipt file missing or unsafe"
            problems.append(entry)
            continue
        raw = load_json(raw_path) if raw_path else None
        if not isinstance(raw, dict):
            entry["reason"] = "raw receipt unreadable"
            problems.append(entry)
            continue
        declared_digest = payload.get("receipt_sha256")
        if declared_digest:
            # Producer rule (kit v1, demo.py journal_receipt): the digest is
            # sha256 of json.dumps(receipt, sort_keys=True); the raw file
            # digest is also accepted (other producers).
            producer_rule = sha256_hex(json.dumps(raw, sort_keys=True).encode("utf-8"))
            if declared_digest not in (actual_sha, producer_rule):
                entry["reason"] = "receipt_sha256 mismatch (raw file altered?)"
                entry["declared"] = declared_digest
                entry["actual_raw_file"] = actual_sha
                entry["actual_producer_rule"] = producer_rule
                problems.append(entry)
                continue
        if payload.get("status") is not None and raw.get("status") != payload.get("status"):
            entry["status"] = {"declared": payload.get("status"), "raw": raw.get("status")}
            problems.append(entry)
            continue
        if raw.get("status") == "0x0":
            # a reverted transaction carries no Transfer log: nothing to cross
            entry["note"] = "reverted transaction (status 0x0) — no Transfer log to cross"
            continue
        if intent is not None:
            transfer = None
            for log in raw.get("logs") or []:
                topics = log.get("topics") or []
                if len(topics) == 3 and str(topics[0]).lower() == TRANSFER_TOPIC:
                    transfer = log
                    break
            if transfer is None:
                entry["reason"] = "NO_TRANSFER_LOG"
                problems.append(entry)
                continue
            to_address = _topic_address(transfer["topics"][2])
            try:
                value = int(str(transfer.get("data", "0x0")), 16)
            except (TypeError, ValueError):
                entry["reason"] = "LOG_DATA_UNREADABLE"
                problems.append(entry)
                continue
            mismatches = []
            if str(transfer.get("address", "")).lower() != str(intent.get("asset", "")).lower():
                mismatches.append("TOKEN_CONTRACT_MISMATCH")
            if not _masked_match(str(intent.get("recipient", "")), to_address):
                mismatches.append("RECIPIENT_MISMATCH")
            try:
                if int(str(intent.get("amount_base_units", ""))) != value:
                    mismatches.append("AMOUNT_MISMATCH")
            except (TypeError, ValueError):
                mismatches.append("AMOUNT_UNREADABLE")
            if mismatches:
                entry["mismatches"] = mismatches
                problems.append(entry)
        checks.append(entry)
    ok = not problems
    return [new_check("A8.receipts.cross", "A", ok,
                      {"receipts_checked": len(receipts), "problems": problems})]


# --------------------------------------------------------------------------- #
# B — on-chain re-verification (only with --rpc, B6 §2.5)
# --------------------------------------------------------------------------- #

def _rpc(url: str, method: str, params: List[Any], timeout: float = 20.0) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json",
                                 "User-Agent": "orvyren-verify/1 (+T10)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError("rpc error: %s" % payload["error"])
    return payload.get("result")


def check_b_chain(root: str, manifest: Dict[str, Any], rpc_url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    checks: List[Dict[str, Any]] = []
    expected_chain = manifest.get("chain_id")
    try:
        chain_id_hex = _rpc(rpc_url, "eth_chainId", [])
        chain_id = int(str(chain_id_hex), 16)
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        return ([new_check("B0.chain.available", "B", False,
                           {"reason": "rpc unavailable: %s" % exc}, status="SKIPPED")],
                "unavailable")
    checks.append(new_check("B0.chain.id", "B", chain_id == expected_chain,
                            {"expected": expected_chain, "observed": chain_id}))
    if chain_id != expected_chain:
        return checks, "rogue"
    exec_decl = (manifest.get("streams") or {}).get("exec") or {}
    records = [record for record in read_jsonl(os.path.join(root, exec_decl.get("path", "audit.jsonl")))
               if isinstance(record, dict) and record.get("kind") == "RECEIPT"]
    for record in records:
        payload = record.get("payload") or {}
        tx_hash = payload.get("tx_hash")
        if not tx_hash:
            continue
        try:
            receipt = _rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
        except Exception as exc:  # noqa: BLE001
            checks.append(new_check("B1.receipt.%s" % (tx_hash or "?")[:12], "B", False,
                                    {"reason": str(exc)}, status="SKIPPED"))
            continue
        if receipt is None:
            checks.append(new_check("B1.receipt.%s" % tx_hash[:12], "B", False,
                                    {"reason": "receipt not found on chain"}, status="SKIPPED"))
            continue
        detail = {"status": {"journal": payload.get("status"), "chain": receipt.get("status")},
                  "block": {"journal": payload.get("block_number"),
                            "chain": receipt.get("blockNumber")}}
        try:
            detail["block"]["chain"] = int(str(receipt.get("blockNumber", "0x0")), 16)
        except (TypeError, ValueError):
            checks.append(new_check("B1.receipt.%s" % tx_hash[:12], "B", False,
                                    {"reason": "unreadable blockNumber from rpc: %r"
                                               % receipt.get("blockNumber")},
                                    status="SKIPPED"))
            continue
        ok = (str(receipt.get("status")) == str(payload.get("status"))
              and detail["block"]["chain"] == payload.get("block_number"))
        checks.append(new_check("B1.receipt.%s" % tx_hash[:12], "B", ok, detail))
    return checks, None


# --------------------------------------------------------------------------- #
# C — coverage of the non-replayable (B6 §2.6)
# --------------------------------------------------------------------------- #

def check_c_coverage(root: str, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    streams = manifest.get("streams") or {}
    agent = streams.get("agent") or {}
    if not agent.get("present"):
        checks.append(new_check("C1.agent.journal", "C", True,
                                {"declared_absent": True,
                                 "reason": agent.get("reason", ""),
                                 "meaning": "no LLM in this run; nothing to cover"},
                                status="COVERED"))
    # refs resolution across the exec journal: every intent_id reference must
    # resolve to an INTENT record (B6 §2.6 rule 2, scoped to what v1 records)
    exec_decl = streams.get("exec") or {}
    records = [record for record in read_jsonl(os.path.join(root, exec_decl.get("path", "audit.jsonl")))
               if isinstance(record, dict)]
    intent_ids = {(record.get("payload") or {}).get("intent_id")
                  for record in records if record.get("kind") == "INTENT"}
    submitters = {(record.get("refs") or {}).get("intent_id")
                  for record in records if record.get("kind") in ("SUBMIT", "RECEIPT")}
    dangling: List[Dict[str, Any]] = []
    declared_gaps: List[Dict[str, Any]] = []
    for record in records:
        refs = record.get("refs") or {}
        ref_id = refs.get("intent_id")
        if not ref_id or record.get("kind") == "INTENT" or ref_id in intent_ids:
            continue
        entry = {"seq": record.get("seq"), "kind": record.get("kind"),
                 "ref": ref_id, "run": refs.get("run")}
        if str(ref_id).startswith("forced-"):
            declared_gaps.append(dict(entry, declared=(
                "raw forced attempt — the run C protocol bypasses the intent "
                "pipeline by design")))
        elif record.get("kind") in ("POLICY", "OUTCOME") and ref_id not in submitters:
            declared_gaps.append(dict(entry, declared=(
                "offline-denial attempt — the INTENT record was not journaled "
                "by the kit v1 (declared gap, never hidden)")))
        else:
            dangling.append(entry)
    checks.append(new_check("C2.refs.resolve", "C", not dangling,
                            {"dangling_refs": dangling,
                             "declared_gaps": declared_gaps}, status="COVERED"))
    return checks


# --------------------------------------------------------------------------- #
# Mutations (B6 §2.7 — the 6 tests)
# --------------------------------------------------------------------------- #

def _mutate_copy(root: str) -> str:
    copy = tempfile.mkdtemp(prefix="orvyren_mut_")
    target = os.path.join(copy, "packet")
    shutil.copytree(root, target)
    return target


def _first_existing(root: str, rel_candidates: Sequence[str]) -> Optional[str]:
    for rel in rel_candidates:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return None


def run_mutations(root: str, manifest: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
    """Apply the 6 registered mutations; each must be detected."""
    dossier = manifest.get("dossier") or {}
    exec_rel = ((manifest.get("streams") or {}).get("exec") or {}).get("path", "audit.jsonl")
    decision_rel = (manifest.get("decision") or {}).get("path")
    results: List[Dict[str, Any]] = []

    def offline_failures(target_root: str) -> List[str]:
        checks = []
        checks += check_a1_chains(target_root, load_json(os.path.join(target_root, "manifest.json")) or {})
        checks += check_a2_dossier(target_root, load_json(os.path.join(target_root, "manifest.json")) or {})
        checks += check_a3_hashes(target_root, load_json(os.path.join(target_root, "manifest.json")) or {})
        checks += check_a4_rerender(target_root, load_json(os.path.join(target_root, "manifest.json")) or {})
        checks += check_a8_receipts(target_root, load_json(os.path.join(target_root, "manifest.json")) or {})
        return sorted({check["id"] for check in checks if not check["ok"]})

    def run_case(case_id: str, description: str, expected_prefix: str, mutate) -> None:
        target = _mutate_copy(root)
        try:
            applied = mutate(target)
            if applied is False:
                results.append({"id": case_id, "mutation": description,
                                "detected": False, "failing_checks": [],
                                "note": "mutation could not be applied to this packet"})
                return
            failing = offline_failures(target)
            detected = bool(failing) and any(check_id.startswith(expected_prefix)
                                             for check_id in failing)
            results.append({"id": case_id, "mutation": description,
                            "detected": detected, "failing_checks": failing})
        finally:
            shutil.rmtree(os.path.dirname(target), ignore_errors=True)

    def m1(target: str) -> bool:
        md = _first_existing(target, [dossier.get("md", "")]) if dossier.get("md") else None
        md = md or _first_existing(target, ["dossier_usdc-2023-03.md"])
        if not md:
            return False
        with open(md, "r", encoding="utf-8") as handle:
            text = handle.read()
        if "local" not in text:
            return False
        with open(md, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("local", "l0cal", 1))
        return True

    def m2(target: str) -> bool:
        path = os.path.join(target, exec_rel)
        records = read_jsonl(path)
        if len(records) < 2 or not isinstance(records[1], dict):
            return False
        payload = records[1].get("payload")
        if not isinstance(payload, dict):
            return False
        payload["__tampered__"] = True
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(canonical_json(record) + "\n")
        return True

    def m3(target: str) -> bool:
        if not decision_rel:
            return False
        path = os.path.join(target, decision_rel)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            return False
        mutated = re.sub(r"100\.0", "120.0", text, count=1)
        if mutated == text:
            mutated = text.replace('"verdict"', '"verdict_"', 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(mutated)
        return True

    def m4(target: str) -> bool:
        receipts = [rel for rel in packet_files(target) if rel.startswith("receipts/")
                    and rel.endswith(".json")]
        for rel in sorted(receipts):
            path = os.path.join(target, rel)
            raw = load_json(path)
            if not isinstance(raw, dict):
                continue
            for log in raw.get("logs") or []:
                topics = log.get("topics") or []
                if len(topics) == 3 and str(topics[0]).lower() == TRANSFER_TOPIC:
                    data = str(log.get("data", "0x0"))
                    digits = list(data)
                    for index in range(len(digits) - 1, 1, -1):
                        if digits[index] in "0123456789abcdef":
                            digits[index] = "f" if digits[index] != "f" else "0"
                            break
                    log["data"] = "".join(digits)
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        json.dump(raw, handle, ensure_ascii=False, indent=1, sort_keys=True)
                    return True
        return False

    def m5(target: str) -> bool:
        receipts = [rel for rel in packet_files(target) if rel.startswith("receipts/")
                    and rel.endswith(".json")]
        if not receipts:
            return False
        os.remove(os.path.join(target, sorted(receipts)[-1]))
        return True

    def m6(target: str) -> bool:
        entry = _first_existing(target, ["verify/orvyren_verify.py"])
        if not entry:
            return False
        with open(entry, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("# tampered\n")
        return True

    run_case("M1", "1 byte of the dossier md body (outside the self field)", "A2", m1)
    run_case("M2", "1 character inside an audit.jsonl line", "A1", m2)
    run_case("M3", "1 changed digit in decision_*.json (an amount)", "A3", m3)
    run_case("M4", "1 changed amount in a raw receipt", "A8", m4)
    run_case("M5", "removal of a receipt file", "A3", m5)
    run_case("M6", "1 modified line of the frozen verifier", "A3", m6)
    all_detected = all(entry.get("detected") for entry in results)
    return results, all_detected


# --------------------------------------------------------------------------- #
# Report assembly and CLI
# --------------------------------------------------------------------------- #

def verify_packet(target: str, *, rpc_url: Optional[str] = None,
                  manifest_only: bool = False, strict: bool = False,
                  with_mutations: bool = False) -> Dict[str, Any]:
    root, cleanup, error = resolve_target(target)
    if error or root is None:
        return {"usage_error": error or "target resolution failed"}
    timeline: Dict[str, Any] = {}
    try:
        manifest = load_json(os.path.join(root, "manifest.json"))
        if not isinstance(manifest, dict):
            checks = [new_check("MANIFEST", "A", False,
                                {"missing": "manifest.json (absent or invalid JSON)"})]
            verdict = "FAIL"
        else:
            checks: List[Dict[str, Any]] = []
            checks += check_a1_chains(root, manifest)
            if not manifest_only:
                checks += check_a2_dossier(root, manifest)
                checks += check_a3_hashes(root, manifest)
                checks += check_a4_rerender(root, manifest)
                checks += check_a5_policy(root, manifest)
                checks += check_a6_snapshot(root, manifest)
                checks += check_a7_fixtures(root, manifest)
                checks += check_a8_receipts(root, manifest)
                checks += check_c_coverage(root, manifest)
            rpc_status = "not_requested"
            if rpc_url and not manifest_only:
                chain_checks, rpc_status = check_b_chain(root, manifest, rpc_url)
                checks += chain_checks
            elif not manifest_only:
                checks.append(new_check(
                    "B1.chain.rpc", "B", True,
                    {"reason": "offline — class-B checks SKIPPED; pass --rpc URL to "
                               "re-verify the chain against the public receipts "
                               "(separate verdict)"},
                    status="SKIPPED"))
            a_ok = all(check["ok"] for check in checks if check["class"] == "A")
            b_ok = all(check["ok"] for check in checks
                       if check["class"] == "B" and check["status"] != "SKIPPED")
            c_ok = all(check["ok"] for check in checks if check["class"] == "C")
            if rpc_status == "unavailable":
                verdict = "FAIL" if not a_ok else "OFFLINE_PASS"
                timeline["chain"] = "unavailable"
            elif not a_ok:
                verdict = "FAIL"
            elif rpc_url and b_ok:
                verdict = "PASS"
            elif rpc_url:
                verdict = "FAIL"
            else:
                verdict = "OFFLINE_PASS"
            if not c_ok and strict:
                verdict = "FAIL"
            timeline["rpc_status"] = rpc_status
        mutations: List[Dict[str, Any]] = []
        mutations_ok = None
        if with_mutations and isinstance(manifest, dict):
            mutations, mutations_ok = run_mutations(root, manifest)
            if not mutations_ok:
                verdict = "FAIL"
        summary = {
            "A": sum(1 for check in checks if check["class"] == "A"),
            "B": sum(1 for check in checks if check["class"] == "B"),
            "C": sum(1 for check in checks if check["class"] == "C"),
            "failed": sum(1 for check in checks if not check["ok"]),
        }
        report = {
            "v": 1,
            "generated_at_utc": utc_now_iso(),
            "target": os.path.abspath(target),
            "verifier": {"name": VERIFIER_NAME, "version": VERIFIER_VERSION,
                         "mode": "rpc" if rpc_url else "offline",
                         "frozen_imports": _FROZEN_MODE},
            "verdict": verdict,
            "checks": checks,
            "dangling_refs": [entry for check in checks
                              if check["id"] == "C2.refs.resolve"
                              for entry in check["detail"].get("dangling_refs", [])],
            "mutations": mutations,
            "summary": summary,
        }
        if timeline:
            report["network"] = timeline
        return report
    finally:
        if cleanup:
            shutil.rmtree(cleanup, ignore_errors=True)


def render_markdown(report: Dict[str, Any]) -> str:
    lines = ["# ORVYREN verify report",
             "",
             "- target: `%s`" % report.get("target"),
             "- verifier: %s %s (%s)" % (report["verifier"]["name"],
                                         report["verifier"]["version"],
                                         report["verifier"]["mode"]),
             "- generated: %s" % report.get("generated_at_utc"),
             "",
             "## VERDICT: %s" % report.get("verdict"),
             ""]
    for cls in ("A", "B", "C"):
        section = [check for check in report["checks"] if check["class"] == cls]
        if not section:
            continue
        lines.append("### Class %s" % cls)
        lines.append("")
        lines.append("| check | status | ok | detail |")
        lines.append("| --- | --- | --- | --- |")
        for check in section:
            detail = canonical_json(check["detail"])[:220]
            lines.append("| %s | %s | %s | `%s` |" % (check["id"], check["status"],
                                                      "yes" if check["ok"] else "NO", detail))
        lines.append("")
    if report.get("mutations"):
        lines.append("### Mutation self-test")
        lines.append("")
        for entry in report["mutations"]:
            lines.append("- %s — %s: %s (`%s`)" % (
                entry["id"], entry["mutation"],
                "detected" if entry["detected"] else "NOT DETECTED",
                ", ".join(entry.get("failing_checks", []))))
        lines.append("")
    if report.get("mutations"):
        lines.append("")
    lines.append("### Summary")
    lines.append("")
    lines.append("`%s`" % canonical_json(report["summary"]))
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m orvyren.verify",
        description="ORVYREN third-party verifier (T10): recompute the "
                    "determinant checks of an audit packet, offline by default.")
    parser.add_argument("target", nargs="?", default=".",
                        help="audit_packet_*.zip or an extracted packet directory")
    parser.add_argument("--offline", action="store_true",
                        help="no network (default; class B checks are SKIPPED)")
    parser.add_argument("--rpc", nargs="?", const="https://sepolia.base.org",
                        default=None, help="re-verify on-chain facts via RPC "
                        "(default URL: Base Sepolia public)")
    parser.add_argument("--manifest-only", action="store_true",
                        help="only manifest-level checks (fast pre-flight)")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="write the machine report to this path")
    parser.add_argument("--mutate-test", action="store_true",
                        help="run the 6-mutation self-test (B6 §2.7)")
    parser.add_argument("--strict", action="store_true",
                        help="fail when a class C element lacks full journal coverage")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the final verdict line")
    args = parser.parse_args(argv)

    if args.offline and args.rpc:
        parser.error("--offline and --rpc are mutually exclusive")
    rpc_url = None if args.offline else args.rpc

    report = verify_packet(args.target, rpc_url=rpc_url,
                           manifest_only=args.manifest_only, strict=args.strict,
                           with_mutations=args.mutate_test)
    if "usage_error" in report:
        print("usage error: %s" % report["usage_error"], file=sys.stderr)
        return 2

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
    md_path = None
    if args.json_path:
        md_path = os.path.splitext(args.json_path)[0] + ".md"
        with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_markdown(report))

    if not args.quiet:
        for check in report["checks"]:
            print("CHECK %-28s %-11s %s" % (check["id"], check["status"],
                                            "ok" if check["ok"] else "FAILED"))
            if not check["ok"]:
                print("      detail: %s" % canonical_json(check["detail"])[:400])
        for entry in report.get("mutations", []):
            print("MUTATION %s %s (%s)" % (entry["id"],
                                           "detected" if entry["detected"] else "NOT DETECTED",
                                           ", ".join(entry.get("failing_checks", []))))
    print("VERDICT: %s — %d checks, %d failed, mutations %s"
          % (report["verdict"], len(report["checks"]), report["summary"]["failed"],
             ("%d/%d" % (sum(1 for entry in report.get("mutations", []) if entry["detected"]),
                         len(report.get("mutations", [])))) if report.get("mutations") else "n/a"))

    if report.get("network", {}).get("rpc_status") == "unavailable":
        return 3
    return 0 if report["verdict"] in ("PASS", "OFFLINE_PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
