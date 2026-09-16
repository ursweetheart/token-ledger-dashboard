# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.11.7@sha256:240fb85ab0f263ef12f492d8476aa3a2e4e1e333f7d67fbdd923d00a506a516a AS uvbin
FROM python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e
WORKDIR /app
COPY --from=uvbin /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libssl-dev nodejs npm libsndfile1 libatomic1 && rm -rf /var/lib/apt/lists/*
ENV UV_PROJECT_ENVIRONMENT=/app/.venv UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:${PATH}" PRISMA_USE_GLOBAL_NODE=true
COPY pyproject.toml uv.lock ./
COPY enterprise/pyproject.toml enterprise/
COPY litellm-proxy-extras/pyproject.toml litellm-proxy-extras/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --no-install-workspace --no-default-groups --no-editable --extra proxy --extra extra_proxy --python python3.13
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-default-groups --no-editable --extra proxy --extra extra_proxy --python python3.13
RUN prisma generate --schema=./schema.prisma
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN python -c "import sys,uvloop,tiktoken; assert sys.version_info[:2] == (3,13); tiktoken.get_encoding('cl100k_base'); tiktoken.get_encoding('o200k_base'); from litellm._redis import _SENTINEL_IGNORED_CONNECTION_ARGS; assert {'host','port'} <= _SENTINEL_IGNORED_CONNECTION_ARGS"
ENTRYPOINT ["litellm"]
CMD ["--config=/app/smoke.yaml", "--port", "4000"]
