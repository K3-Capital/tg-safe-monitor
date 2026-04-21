FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md .python-version* uv.lock* /app/
COPY src /app/src

RUN uv sync --locked --no-dev

CMD ["uv", "run", "python", "-m", "tg_safe_monitor"]
