# ORVYREN-Core — single-entry reproduction commands (POSIX / Git-Bash).
#
# Everything runs offline except:
#   - `docker-test` / `docker-ui`: image build (pip install needs network);
#   - `make ui`: local server, no outbound network.
#
# The core is stdlib-only; eth-account (requirements.txt) is only used by the
# signer kit and is never imported by the core test suite.

PYTHON ?= python
CASE ?= usdc-2023-03
HOST ?= 127.0.0.1
PORT ?= 8000
IMAGE ?= orvyren:dev
COMPOSE ?= docker compose

# Versioned v2 audit packet (reference: evidence/audit_packets/README.md).
AUDIT_PACKET ?= evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip

# Windows cp1252 console -> UTF-8, same settings as the Docker image and CI.
export PYTHONIOENCODING := utf-8
export PYTHONUNBUFFERED := 1
export PYTHONUTF8 := 1
# `python -m orvyren.decide` needs src/ on the path: the package is not
# installed (no [build-system] in pyproject.toml, deliberately).
export PYTHONPATH := src

.DEFAULT_GOAL := help

.PHONY: help test test-clone demo replay ui verify lint docker-build docker-test docker-ui clean

help:
	@echo "ORVYREN — reproduction targets"
	@echo "  make test         full unittest suite (verbose)"
	@echo "  make test-clone   suite on a pristine clone of HEAD (git archive)"
	@echo "  make demo         full offline decision (python -m orvyren.decide)"
	@echo "  make replay       bit-for-bit journal replay of case $(CASE)"
	@echo "  make ui           offline UI on http://$(HOST):$(PORT)"
	@echo "  make verify       T10 verification of the versioned v2 audit packet"
	@echo "  make lint         ruff (fallback: compileall) on src/ and tests/"
	@echo "  make docker-test  build the image + run the suite in the container"
	@echo "  make docker-ui    UI in a container (docker compose up ui)"
	@echo "  make clean        purge local Python caches"

test:
	$(PYTHON) -m unittest discover -s tests -v

# Guarantees the suite is green on a tree WITHOUT untracked files
# (dist/, caches...): that is the definition of a reproducible clone.
test-clone:
	@tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT INT TERM; \
	echo "== pristine clone of HEAD -> $$tmp"; \
	git archive HEAD | tar -x -C "$$tmp"; \
	cd "$$tmp" && $(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m orvyren.decide --case $(CASE) --replay

replay:
	$(PYTHON) run_replay.py journal --case $(CASE)

ui:
	$(PYTHON) run_audit.py --serve --host $(HOST) --port $(PORT)

verify:
	$(PYTHON) run_verify.py "$(AUDIT_PACKET)"

# Blocking gate = fatal errors (syntax, undefined names): the v1 baseline is
# frozen (FREEZE_V2), so no mass reformatting is allowed. The compileall
# fallback at least checks that everything compiles when ruff is not installed.
lint:
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src tests; \
	elif $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		$(PYTHON) -m ruff check src tests; \
	else \
		echo "ruff not installed — falling back to compileall (syntax check)"; \
		$(PYTHON) -m compileall -q src tests; \
	fi

docker-build:
	docker build -t $(IMAGE) .

docker-test: docker-build
	docker run --rm $(IMAGE)

docker-ui: docker-build
	$(COMPOSE) up ui

clean:
	find . -path ./.git -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -path ./.git -prune -o -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache
