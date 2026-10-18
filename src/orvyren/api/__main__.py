"""``python -m orvyren.api`` — start the ORVYREN live dashboard server."""

from __future__ import annotations

from orvyren.api.config import load_settings


def main() -> None:
    settings = load_settings()
    from orvyren.api.main import run_server

    run_server(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
