#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ethereum **archive** JSON-RPC client (ORVYREN-Core data layer).

Why this module exists
----------------------
Reconstructing a past episode (rsETH 2026-04, stETH 2022-06) means reading
contract state *at a historical block*.  Two free, key-less public archives
serve that state and were measured on 2026-10-15 (research/W2A, research/W2B):

* ``https://eth.drpc.org``                     -- archive ``eth_call`` OK;
* ``https://eth-mainnet.public.blastapi.io``   -- same answers, used as fallback.

Non-archival endpoints (``ethereum.publicnode.com``, ``1rpc.io/eth``,
``rpc.flashbots.net``, ``cloudflare-eth.com``) refuse historical state and are
deliberately *not* used.

Guarantees provided here
------------------------
* **Fallback**: each request walks the endpoint list; a transport failure is
  retried on the same endpoint (``retries``), a node-level JSON-RPC error moves
  straight to the next endpoint.
* **Clear errors**: :class:`RpcError` carries the method, the endpoints tried and
  the last failure reason.  :class:`RpcRangeError` flags the measured free-tier
  limit on ``eth_getLogs`` (10 000 blocks per request).
* **block <-> timestamp**: :meth:`ArchiveRpc.block_at_timestamp` returns the last
  block whose timestamp is <= the target, using a secant/bisection hybrid that
  starts from measured anchors (see :data:`CHAIN_ANCHORS`); every timestamp read
  is cached, so a series costs ~2-3 calls per point instead of ~20.
* **Pagination**: :meth:`ArchiveRpc.get_logs` splits any range into chunks of at
  most :data:`MAX_GET_LOGS_RANGE` blocks and concatenates the results.

Standard library only (``urllib``, ``json``, ``time``).
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "DEFAULT_RPC_URLS",
    "MAX_GET_LOGS_RANGE",
    "CHAIN_ANCHORS",
    "RpcError",
    "RpcRangeError",
    "ArchiveRpc",
    "encode_uint",
    "encode_int",
    "encode_address",
    "decode_words",
    "decode_uint",
    "decode_int",
    "decode_address",
    "decode_string",
    "hex_to_int",
    "is_address",
]

#: Free public archive endpoints, in preference order (measured 2026-10-15).
DEFAULT_RPC_URLS: Tuple[str, ...] = (
    "https://eth.drpc.org",
    "https://eth-mainnet.public.blastapi.io",
)

#: Measured free-tier ceiling of ``eth_getLogs`` on both endpoints:
#: "ranges over 10000 blocks are not supported on free plan" (HTTP 400).
MAX_GET_LOGS_RANGE = 10_000

#: (block, unix timestamp) pairs measured on-chain (research/W2A, research/W2B).
#: They only seed the block<->timestamp search; every returned block is checked
#: against the chain itself.  **Block 0 is deliberately absent**: the genesis
#: header carries ``timestamp = 0`` (only block 1 holds 2015-07-30T15:26:28Z),
#: which would poison any linear model anchored there.
CHAIN_ANCHORS: Tuple[Tuple[int, int], ...] = (
    (1, 1438269988),          # first block with a real timestamp - 2015-07-30T15:26:28Z
    (14720000, 1651791602),   # 2022-05-05T23:00:02Z (W2-A stETH series)
    (14970303, 1655337663),   # 2022-06-16T00:01:03Z (W2-A, stETH/Celsius)
    (15537394, 1663224179),   # The Merge - 2022-09-15T06:42:59Z
    (16801143, 1678492799),   # 2023-03-10T23:59:59Z (W2-A, USDC/SVB)
    (24908723, 1776539039),   # 2026-04-18T19:03:59Z (W2-B, rsETH freeze block)
)

#: ``transport(url, payload, timeout) -> bytes``.  Injectable so tests can run
#: the whole client (fallback, search, pagination) without touching a network.
Transport = Callable[[str, bytes, float], bytes]

_USER_AGENT = "orvyren-core/0.1 (archive reader; python-urllib)"

#: Masked placeholder for credential-bearing URL parts (same convention and
#: deny-by-default rule as ``orvyren.execution.guard.mask_rpc_url`` — F08: a
#: credential may sit at the FRONT of the path, so only version-like tokens
#: such as ``v2`` stay visible).  Kept local so the data layer stays
#: standalone; see tests/test_execution_review.py for both implementations.
_MASK = "***"


def _mask_endpoint(url: str) -> str:
    """Host kept readable, credentials masked; never raises (malformed -> full mask)."""
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(str(url))
        if not parts.scheme or not parts.hostname:
            return _MASK
        netloc = parts.hostname
        if parts.port:
            netloc += f":{parts.port}"
        if parts.username or parts.password:
            netloc = f"{_MASK}@{netloc}"
        segments = [segment for segment in (parts.path or "").split("/") if segment]
    except ValueError:
        return _MASK
    if not segments:
        return f"{parts.scheme}://{netloc}"
    shown = [segment if segment[:1] == "v" and segment[1:].isdigit() else _MASK
             for segment in segments]
    return f"{parts.scheme}://{netloc}/" + "/".join(shown)

#: JSON-RPC errors that are contract-level answers, not endpoint failures: every
#: endpoint (and every retry) returns the same thing, so we stop immediately.
_TERMINAL_ERROR_MARKERS = ("execution reverted", "invalid opcode", "out of gas", "invalid argument")


class RpcError(RuntimeError):
    """A JSON-RPC request failed on every endpoint (message says which)."""


class RpcRangeError(RpcError):
    """``eth_getLogs`` range refused by the endpoint (free-tier limit)."""


def _http_post(url: str, payload: bytes, timeout: float) -> bytes:
    """Default one-shot transport: one HTTP POST, no retry (the client retries)."""
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (fixed https endpoints)
        return response.read()


class HttpTransport:
    """Keep-alive POST transport -- one persistent connection per endpoint.

    A cold TLS handshake costs ~0.3-0.5 s on the public archives, which would
    dominate a few thousand ``eth_call`` reads; reusing the connection divides
    the wall time of a reconstruction by roughly three.  A failed/stale
    connection is closed and retried once with a fresh one.
    """

    def __init__(self, user_agent: str = _USER_AGENT) -> None:
        self.user_agent = user_agent
        self._conns: Dict[str, Tuple[http.client.HTTPConnection, str]] = {}

    def _connect(self, url: str, timeout: float) -> Tuple[http.client.HTTPConnection, str]:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise ValueError(f"unsupported endpoint scheme in {url!r}")
        factory = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        connection = factory(parts.netloc, timeout=timeout)
        return connection, parts.path or "/"

    def close(self) -> None:
        """Drop every cached connection."""
        for connection, _ in self._conns.values():
            try:
                connection.close()
            except Exception:
                pass
        self._conns.clear()

    def __call__(self, url: str, payload: bytes, timeout: float) -> bytes:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "Content-Length": str(len(payload)),
        }
        last_error: Optional[Exception] = None
        for attempt in (0, 1):
            connection, path = self._connect(url, timeout) if url not in self._conns else self._conns[url]
            try:
                connection.request("POST", path, body=payload, headers=headers)
                response = connection.getresponse()
                body = response.read()
                if response.status != 200:
                    raise RpcError(f"HTTP {response.status} from {_mask_endpoint(url)}: {body[:200]!r}")
                self._conns[url] = (connection, path)
                return body
            except Exception as exc:  # stale keep-alive connection, timeout, TLS reset...
                last_error = exc
                try:
                    connection.close()
                except Exception:
                    pass
                self._conns.pop(url, None)
        raise RpcError(f"{_mask_endpoint(url)}: {type(last_error).__name__}: {last_error}")


# --------------------------------------------------------------------------- #
# ABI helpers (uint256/int128 words, addresses, dynamic strings)
# --------------------------------------------------------------------------- #
def hex_to_int(value: Any) -> int:
    """Accept ``int``, ``"0x.."`` or ``"deadbeef"`` and return the integer."""
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text, 16)


def is_address(value: str) -> bool:
    """True for a 20-byte ``0x`` address."""
    if not isinstance(value, str) or not value.startswith("0x") or len(value) != 42:
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value[2:])


def encode_uint(value: int) -> str:
    """Encode a non-negative integer as one 32-byte word (no ``0x``).

    Strictly integral: ``int()`` coercion would silently truncate a float
    (``encode_uint(1.5)`` -> 1) or accept ``True`` as 1 — a corrupted amount
    must fail loudly, never encode.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"encode_uint expects an int, got {value!r}")
    number = value
    if number < 0:
        raise ValueError(f"encode_uint expects a non-negative integer, got {value!r}")
    if number >= 1 << 256:
        raise ValueError("encode_uint overflow: value does not fit in 256 bits")
    return f"{number:064x}"


def encode_int(value: int) -> str:
    """Encode a signed integer (e.g. Curve ``int128`` index) as one 32-byte word."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"encode_int expects an int, got {value!r}")
    number = value
    if number < 0:
        if number < -(1 << 255):
            raise ValueError("encode_int underflow: value does not fit in int256")
        number += 1 << 256
    if number >= 1 << 256:
        raise ValueError("encode_int overflow: value does not fit in int256")
    return f"{number:064x}"


def encode_address(address: str) -> str:
    """Left-pad an address to one 32-byte word (no ``0x``)."""
    if not is_address(address):
        raise ValueError(f"invalid 20-byte address: {address!r}")
    return address[2:].lower().rjust(64, "0")


def _raw_hex(data: str) -> str:
    text = data[2:] if isinstance(data, str) and data.startswith("0x") else str(data)
    if len(text) % 64:
        raise ValueError(f"ABI payload is not a whole number of 32-byte words: {len(text)} hex chars")
    return text


def decode_words(data: str) -> List[int]:
    """Split an ABI return payload into its 32-byte words (as integers)."""
    text = _raw_hex(data)
    return [int(text[i:i + 64], 16) for i in range(0, len(text), 64)]


def decode_uint(data: str, index: int = 0) -> int:
    """Return word ``index`` of an ABI payload as an unsigned integer."""
    words = decode_words(data)
    try:
        return words[index]
    except IndexError as exc:
        raise ValueError(
            f"word index {index} out of range: payload holds {len(words)} word(s)"
        ) from exc


def decode_int(data: str, index: int = 0) -> int:
    """Return word ``index`` of an ABI payload as a two's-complement int256."""
    word = decode_uint(data, index)
    return word - (1 << 256) if word >= 1 << 255 else word


def decode_address(word: Any) -> str:
    """Turn a 32-byte word (int or hex) into a lowercase ``0x`` address."""
    value = word if isinstance(word, int) else hex_to_int(word)
    if value < 0 or value >= 1 << 160:
        raise ValueError("word is not a 20-byte address")
    return "0x" + f"{value:040x}"


def decode_string(data: str) -> str:
    """Decode an ABI-encoded dynamic ``string`` (offset, length, bytes)."""
    words = _raw_hex(data)
    if len(words) < 128:
        return ""
    offset = int(words[0:64], 16) * 2
    if offset + 64 > len(words):
        raise ValueError(
            f"ABI string offset out of range: {offset // 2} bytes into a "
            f"{len(words) // 2}-byte payload"
        )
    length = int(words[offset:offset + 64], 16)
    payload = words[offset + 64:offset + 64 + length * 2]
    if len(payload) != length * 2:
        raise ValueError("truncated ABI string payload")
    return bytes.fromhex(payload).decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class ArchiveRpc:
    """Archive JSON-RPC client with endpoint fallback, caching and pagination.

    >>> rpc = ArchiveRpc()                      # doctest: +SKIP
    >>> rpc.eth_block_number()                  # doctest: +SKIP
    >>> rpc.eth_call("0xA0b8...", "0x18160ddd", 16_801_143)   # doctest: +SKIP
    """

    def __init__(
        self,
        urls: Optional[Sequence[str]] = None,
        *,
        timeout: float = 30.0,
        retries: int = 2,
        backoff: float = 0.7,
        min_interval: float = 0.0,
        transport: Optional[Transport] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.urls: Tuple[str, ...] = tuple(urls) if urls else DEFAULT_RPC_URLS
        if not self.urls:
            raise ValueError("ArchiveRpc needs at least one endpoint URL")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.backoff = float(backoff)
        self.min_interval = float(min_interval)
        self._transport: Transport = transport or HttpTransport(user_agent or _USER_AGENT)
        self.user_agent = user_agent or _USER_AGENT
        # provenance / observability
        self.calls = 0
        self.errors = 0
        self.url_hits: Dict[str, int] = {}
        self.last_url: Optional[str] = None
        # caches
        self._timestamp_cache: Dict[int, int] = {}

    # -- transport ---------------------------------------------------------- #
    def _post(self, url: str, payload: bytes) -> bytes:
        return self._transport(url, payload, self.timeout)

    def call(self, method: str, params: Sequence[Any], *, url: Optional[str] = None) -> Any:
        """Send one JSON-RPC request, walking endpoints until one answers."""
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)},
            separators=(",", ":"),
        ).encode("utf-8")
        endpoints = (url,) if url else self.urls
        failures: List[str] = []
        for endpoint in endpoints:
            for attempt in range(self.retries + 1):
                if self.min_interval:
                    time.sleep(self.min_interval)
                self.calls += 1
                try:
                    raw = self._post(endpoint, payload)
                except Exception as exc:  # transport-level: retry the same endpoint
                    self.errors += 1
                    failures.append(f"{_mask_endpoint(endpoint)}: {type(exc).__name__}: {exc}")
                    if attempt < self.retries:
                        time.sleep(self.backoff * (attempt + 1))
                    continue
                try:
                    body = json.loads(raw.decode("utf-8", "replace"))
                except Exception as exc:
                    self.errors += 1
                    failures.append(f"{_mask_endpoint(endpoint)}: invalid JSON response ({exc})")
                    break
                # A JSON-RPC success carries "result" (possibly null: an unknown
                # block/receipt is a valid *answer*, not an endpoint failure).
                if isinstance(body, dict) and body.get("error") is None and "result" in body:
                    self.url_hits[endpoint] = self.url_hits.get(endpoint, 0) + 1
                    self.last_url = endpoint
                    return body["result"]
                error = (body or {}).get("error") if isinstance(body, dict) else body
                self.errors += 1
                failures.append(f"{_mask_endpoint(endpoint)}: {method} refused -> {error}")
                if any(marker in str(error).lower() for marker in _TERMINAL_ERROR_MARKERS):
                    # Contract-level answer: identical on every endpoint, stop here.
                    raise RpcError(
                        f"{method} refused by the contract at {_mask_endpoint(endpoint)}: {error}")
                break  # node-level answer: the other endpoint may still hold archive state
        raise RpcError(
            f"{method}: no endpoint answered ({len(endpoints)} tried). "
            + " | ".join(failures[-3:])
        )

    # -- primitives --------------------------------------------------------- #
    @staticmethod
    def _block_tag(block: Any) -> str:
        if isinstance(block, bool):
            raise TypeError("block must be an int, a hex string or 'latest'")
        if isinstance(block, int):
            if block < 0:
                raise ValueError(f"block number must be >= 0, got {block}")
            return hex(block)
        return str(block)

    def eth_block_number(self) -> int:
        """Head block number (``eth_blockNumber``)."""
        return hex_to_int(self.call("eth_blockNumber", []))

    def get_block(self, block: Any = "latest", *, full_transactions: bool = False) -> Dict[str, Any]:
        """Full block object (``eth_getBlockByNumber``)."""
        result = self.call("eth_getBlockByNumber", [self._block_tag(block), bool(full_transactions)])
        if not isinstance(result, dict):
            raise RpcError(f"eth_getBlockByNumber({self._block_tag(block)}) returned {result!r}")
        return result

    def eth_call(self, to: str, data: str, block: Any = "latest") -> str:
        """Read-only ``eth_call`` against contract state *at* ``block``."""
        if not is_address(to):
            raise ValueError(f"invalid contract address: {to!r}")
        if not isinstance(data, str) or not data.startswith("0x"):
            raise ValueError(f"invalid calldata: {data!r}")
        return str(self.call("eth_call", [{"to": to, "data": data}, self._block_tag(block)]))

    def get_code(self, address: str, block: Any = "latest") -> str:
        """Contract bytecode at ``block`` (``0x`` when no code is deployed there)."""
        if not is_address(address):
            raise ValueError(f"invalid contract address: {address!r}")
        return str(self.call("eth_getCode", [address, self._block_tag(block)]))

    def block_timestamp(self, block: Any) -> int:
        """Unix timestamp of ``block`` (cached; ``block`` may be an int or hex tag)."""
        if isinstance(block, int):
            cached = self._timestamp_cache.get(block)
            if cached is not None:
                return cached
            stamp = hex_to_int(self.get_block(block)["timestamp"])
            self._timestamp_cache[block] = stamp
            return stamp
        return hex_to_int(self.get_block(block)["timestamp"])

    def block_at_timestamp(
        self,
        timestamp: int,
        *,
        low: int = 0,
        high: Optional[int] = None,
        max_attempts: int = 64,
    ) -> int:
        """Last block whose timestamp is <= ``timestamp`` (<= 12 s of slack).

        Starts from the measured anchors, then alternates a secant estimate with
        bound updates, so a series costs ~2-3 ``eth_getBlockByNumber`` calls per
        point on top of the cached anchors.
        """
        target = int(timestamp)
        head = self.eth_block_number() if high is None else int(high)
        lo, hi = int(low), head
        if lo >= hi:
            raise ValueError(f"invalid block window for timestamp search: low={lo} high={hi}")

        for anchor_block, anchor_ts in CHAIN_ANCHORS:
            if anchor_block <= lo or anchor_block >= hi:
                continue
            if anchor_ts <= target:
                lo = anchor_block
            else:
                hi = anchor_block

        t_lo, t_hi = self.block_timestamp(lo), self.block_timestamp(hi)
        if target < t_lo:
            raise RpcError(
                f"timestamp {target} precedes block {lo} ({t_lo}); widen the search window"
            )
        if target >= t_hi:
            # Target at/after the head (or after `high`): the head block is the best answer.
            return hi

        for _ in range(max_attempts):
            if hi - lo <= 1:
                return lo
            span = t_hi - t_lo
            if span <= 0:
                est = (lo + hi) // 2
            else:
                est = lo + int((target - t_lo) * (hi - lo) / span)
            # Bisection guard: a secant estimate that lands near a bound barely shrinks
            # the window, and a model anchored on a bad timestamp can crawl for ever
            # (measured: a full-range search on 2022-05-01 stalled at block 0 because
            # block 0's timestamp is 0).  When the estimate is not comfortably inside
            # the window, fall back to the midpoint, which halves it.
            margin = max(1, (hi - lo) // 16)
            if not lo + margin <= est <= hi - margin:
                est = (lo + hi) // 2
            if est <= lo:
                est = lo + 1
            elif est >= hi:
                est = hi - 1
            t_est = self.block_timestamp(est)
            if t_est <= target:
                lo, t_lo = est, t_est
            else:
                hi, t_hi = est, t_est
        return lo

    def get_logs(
        self,
        *,
        from_block: int,
        to_block: int,
        address: Optional[str] = None,
        topics: Optional[Sequence[Any]] = None,
        chunk_size: int = MAX_GET_LOGS_RANGE,
    ) -> List[Dict[str, Any]]:
        """``eth_getLogs`` over a range, paginated to the measured free-tier limit.

        ``chunk_size`` may not exceed :data:`MAX_GET_LOGS_RANGE` (10 000): the
        public archives answer "ranges over 10000 blocks are not supported on
        free plan" above that.
        """
        start, end = int(from_block), int(to_block)
        if end < start:
            raise ValueError(f"empty log range: from_block={start} > to_block={end}")
        if chunk_size <= 0 or chunk_size > MAX_GET_LOGS_RANGE:
            raise ValueError(
                f"chunk_size must be in 1..{MAX_GET_LOGS_RANGE} (free-tier limit), got {chunk_size}"
            )
        logs: List[Dict[str, Any]] = []
        cursor = start
        while cursor <= end:
            stop = min(cursor + chunk_size - 1, end)
            params: Dict[str, Any] = {"fromBlock": hex(cursor), "toBlock": hex(stop)}
            if address is not None:
                if not is_address(address):
                    raise ValueError(f"invalid log filter address: {address!r}")
                params["address"] = address
            if topics is not None:
                params["topics"] = list(topics)
            try:
                chunk = self.call("eth_getLogs", [params])
            except RpcError as exc:
                raise RpcRangeError(
                    f"eth_getLogs [{cursor}, {stop}] refused: {exc} | free public endpoints cap "
                    f"a single request at {MAX_GET_LOGS_RANGE} blocks"
                ) from exc
            if not isinstance(chunk, list):
                raise RpcError(
                    f"eth_getLogs [{cursor}, {stop}] returned {type(chunk).__name__}, "
                    f"expected a list of logs"
                )
            logs.extend(chunk)
            cursor = stop + 1
        return logs

    # -- provenance --------------------------------------------------------- #
    def provenance(self) -> Dict[str, Any]:
        """What this client actually did (sources, call counts, calls per endpoint).

        Endpoint URLs are masked (F08) so a credential-bearing URL can never
        land in an evidence file through this payload.
        """
        return {
            "endpoints": [_mask_endpoint(url) for url in self.urls],
            "calls": self.calls,
            "errors": self.errors,
            "hits": {_mask_endpoint(url): count
                     for url, count in sorted(self.url_hits.items())},
            "last_url": _mask_endpoint(self.last_url) if self.last_url else None,
        }

    def close(self) -> None:
        """Release the underlying transport (keep-alive connections, files...)."""
        closer = getattr(self._transport, "close", None)
        if callable(closer):
            closer()

    def __enter__(self) -> "ArchiveRpc":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
        return None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ArchiveRpc(urls={self.urls!r}, calls={self.calls})"
