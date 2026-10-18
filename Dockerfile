# syntax=docker/dockerfile:1
# ORVYREN-Core — reproduction image (tests + offline UI).
#
# Multi-stage: runtime dependencies (eth-account, the only third-party
# dependency, used by the signer kit) are installed into an isolated venv in
# the builder stage; the final image only carries that venv plus the repo.
#
#   docker build -t orvyren:dev .
#   docker run --rm orvyren:dev                      # unittest -v suite
#   docker run --rm -p 8000:8000 orvyren:dev \
#       python run_audit.py --serve --host 0.0.0.0 --port 8000

FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime

# UTF-8 forced: the Windows cp1252 console must never leak into outputs
# (JSON, dossiers, logs); same settings as CI and the Makefile.
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="/opt/venv/bin:$PATH"

# Non-root user: the image never runs as root.
RUN groupadd --gid 10001 orvyren \
    && useradd --uid 10001 --gid orvyren --create-home --shell /usr/sbin/nologin orvyren

WORKDIR /app

# Dependencies are installed once in the builder (layer cache).
COPY --from=builder /opt/venv /opt/venv

# The build context is filtered by .dockerignore (.git, secrets, dist/...).
COPY . .

# The repo is writable by the non-root user: some runs write artifacts
# (evidence/, replay/runs.jsonl — evidence/demo_runs/ included) inside the tree.
RUN chown -R orvyren:orvyren /app

USER orvyren

# Offline UI (run_audit.py --serve); the tests expose nothing.
EXPOSE 8000

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
