"""Offline, stdlib-only HTTP server for the ORVYREN-Core decision dossier.

Routes
------
``GET /``
    Latest ``evidence/dossier_*.html``. Returns ``503`` with a clear message
    when no dossier has been built yet (the server never crashes on this).
``GET /ui``
    Offline index of the twelve W8 screens (L8.1-L8.3); every screen banner
    carries its mode label and its clock.
``GET /screen/<1-12>``
    One screen, server-rendered HTML — no JavaScript, no external asset.
``GET /api/dossier``
    JSON description of the latest dossier (paths, SHA-256s, case, verdict,
    ``generated_at``), or the decision JSON itself when no dossier exists yet.
``GET /api/health``
    ``{"ok": true, "version": "0.1"}``.

Usage::

    python run_audit.py --serve                  # repository root
    PYTHONPATH=src python -m orvyren.ui.server   # equivalent entry point

No third-party dependency, no external asset, no JavaScript.
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from orvyren.audit import dossier  # noqa: E402
from orvyren.ui import screens  # noqa: E402

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
_REPO_ROOT = os.path.dirname(_SRC_DIR)
_ROUTE_LIST = ["/", "/ui", "/screen/<1-12>", "/api/dossier", "/api/health"]


def resolve_evidence_dir(evidence_dir=None):
    """Absolute evidence directory; defaults to ``<repo>/evidence``."""
    if evidence_dir:
        return os.path.abspath(evidence_dir)
    return os.path.join(_REPO_ROOT, "evidence")


def _latest_decision_json(evidence_dir):
    try:
        names = sorted(os.listdir(evidence_dir))
    except OSError:
        return None
    candidates = []
    for name in names:
        if name.startswith("decision_") and name.endswith(".json"):
            path = os.path.join(evidence_dir, name)
            if os.path.isfile(path):
                candidates.append(path)
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda p: (os.path.getmtime(p), os.path.basename(p)))
    except OSError:
        return max(candidates, key=os.path.basename)


def build_dossier_api_payload(evidence_dir):
    """JSON-able payload returned by ``GET /api/dossier``."""
    html_path = dossier.find_latest_dossier(evidence_dir)
    if html_path:
        md_path = html_path[: -len(".html")] + ".md"
        md_exists = os.path.isfile(md_path)
        meta = dossier.parse_dossier_metadata(md_path) if md_exists else {}
        case = meta.get("case") or os.path.basename(html_path)[len("dossier_"):-len(".html")]
        payload = {
            "ok": True,
            "source": "dossier",
            "case": case,
            "html": html_path,
            "md": md_path if md_exists else None,
            "sha256_md": dossier.sha256_file(md_path) if md_exists else None,
            "sha256_html": dossier.sha256_file(html_path),
            "generated_at": meta.get("generated_at"),
            "verdict": meta.get("verdict"),
        }
        decision_path = os.path.join(evidence_dir, f"decision_{case}.json")
        if os.path.isfile(decision_path):
            try:
                with open(decision_path, "r", encoding="utf-8") as handle:
                    payload["decision"] = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                payload["decision_unreadable"] = f"{decision_path} ({type(exc).__name__})"
        return payload

    decision_path = _latest_decision_json(evidence_dir)
    if decision_path:
        try:
            with open(decision_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "source": "decision_json",
                "path": decision_path,
                "error": f"{type(exc).__name__}: {exc}",
            }
        return {
            "ok": True,
            "source": "decision_json",
            "path": decision_path,
            "sha256": dossier.sha256_file(decision_path),
            "decision": data,
        }

    return {
        "ok": False,
        "error": (
            f"no dossier and no decision JSON found in {evidence_dir}; "
            "build one with 'python run_audit.py'."
        ),
    }


class DossierRequestHandler(BaseHTTPRequestHandler):
    """Read-only handler; every route is guarded so a request cannot kill it."""

    server_version = f"ORVYREN-Core/{dossier.ENGINE_VERSION}"
    sys_version = ""

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            path = urlparse(self.path).path
            if path != "/":
                path = path.rstrip("/") or "/"
            if path == "/":
                self._route_root()
            elif path == "/ui":
                ctx = screens.Ctx(_REPO_ROOT, self.server.evidence_dir)
                self._send(200, "text/html; charset=utf-8", screens.build_index(ctx))
            elif path.startswith("/screen/"):
                self._route_screen(path)
            elif path == "/api/health":
                self._send_json(200, {"ok": True, "version": dossier.ENGINE_VERSION})
            elif path == "/api/dossier":
                payload = build_dossier_api_payload(self.server.evidence_dir)
                self._send_json(200 if payload.get("ok") else 404, payload)
            else:
                self._send_json(
                    404,
                    {
                        "ok": False,
                        "error": f"unknown path: {path}",
                        "routes": _ROUTE_LIST,
                    },
                )
        except Exception as exc:  # defensive: a request must never down the server
            try:
                self._send_json(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
            except Exception:
                self.close_connection = True

    def _route_root(self):
        latest = dossier.find_latest_dossier(self.server.evidence_dir)
        if not latest:
            body = (
                '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
                "<title>ORVYREN-Core - no dossier available</title></head><body>"
                "<h1>503 - no dossier available</h1>"
                f"<p>No <code>dossier_*.html</code> file was found in "
                f"<code>{_escape(self.server.evidence_dir)}</code>.</p>"
                "<p>Build the decision dossier first: <code>python run_audit.py</code>, "
                "then reload this page.</p></body></html>"
            )
            self._send(503, "text/html; charset=utf-8", body.encode("utf-8"))
            return
        try:
            with open(latest, "rb") as handle:
                payload = handle.read()
        except OSError as exc:
            self._send_json(500, {"ok": False, "error": f"cannot read {latest}: {exc}"})
            return
        self._send(200, "text/html; charset=utf-8", payload)

    def _route_screen(self, path):
        ctx = screens.Ctx(_REPO_ROOT, self.server.evidence_dir)
        try:
            screen_id = int(path.split("/", 2)[2])
        except (IndexError, ValueError):
            screen_id = None
        if screen_id not in screens.screen_ids():
            self._send_json(
                404,
                {
                    "ok": False,
                    "error": f"unknown screen: {path}",
                    "screens": [f"/screen/{sid}" for sid in screens.screen_ids()],
                },
            )
            return
        self._send(200, "text/html; charset=utf-8", screens.build_screen(screen_id, ctx))

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, code, payload):
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self._send(code, "application/json; charset=utf-8", body)

    def log_message(self, fmt, *args):
        if getattr(self.server, "quiet", False):
            return
        sys.stderr.write(f"[orvyren-ui] {self.address_string()} - {fmt % args}\n")


def _escape(text):
    from html import escape as _html_escape

    return _html_escape(str(text), quote=True)


def make_server(host=DEFAULT_HOST, port=DEFAULT_PORT, evidence_dir=None, quiet=False):
    """Build a ready-to-serve :class:`ThreadingHTTPServer` (no blocking)."""
    httpd = ThreadingHTTPServer((host, port), DossierRequestHandler)
    httpd.daemon_threads = True
    httpd.evidence_dir = resolve_evidence_dir(evidence_dir)
    httpd.quiet = quiet
    return httpd


def serve(host=DEFAULT_HOST, port=DEFAULT_PORT, evidence_dir=None):
    """Blocking server loop with a friendly startup banner."""
    httpd = make_server(host, port, evidence_dir)
    display_host = host if host not in ("0.0.0.0", "::") else "127.0.0.1"
    print(f"ORVYREN-Core v{dossier.ENGINE_VERSION} dossier server -> http://{display_host}:{httpd.server_address[1]}/")
    print(f"  evidence dir : {httpd.evidence_dir}")
    latest = dossier.find_latest_dossier(httpd.evidence_dir)
    print(f"  dossier      : {latest if latest else 'none yet - GET / returns 503 until one is built'}")
    print("  routes       : / (latest dossier HTML), /ui (12 screens), /screen/1..12, /api/dossier (JSON), /api/health")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        httpd.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="orvyren.ui.server",
        description="Serve the ORVYREN-Core decision dossier over plain HTTP (stdlib only).",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port (default: %(default)s)")
    parser.add_argument(
        "--evidence-dir",
        default=None,
        help="evidence directory to serve (default: <repo>/evidence)",
    )
    args = parser.parse_args(argv)
    serve(args.host, args.port, args.evidence_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
