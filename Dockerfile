FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=src/persona,target=/app/src/persona \
    uv sync --frozen --no-install-project --no-dev --no-editable --group mcp

COPY src/persona/ /app/src/persona
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=/app/README.md \
    uv sync --frozen --no-dev --no-editable --group mcp

FROM python:3.12-slim

WORKDIR /app

COPY --from=uv --chown=app:app /app/.venv /app/.venv
COPY --from=uv --chown=app:app /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["persona"]
