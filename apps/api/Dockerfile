FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG UV_DEFAULT_INDEX=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX}

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/
WORKDIR /app/apps/api
RUN uv sync --frozen --no-dev --no-install-project --default-index "${UV_DEFAULT_INDEX}"
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev --no-editable --default-index "${UV_DEFAULT_INDEX}"

EXPOSE 8000

CMD [".venv/bin/uvicorn", "plugin_hub_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
