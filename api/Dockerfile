FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8080
# Bind :: not 0.0.0.0 — Fly private networking is IPv6, and the SvelteKit
# server is the only caller, reaching this over relative-api.internal.
CMD ["uvicorn", "app.main:app", "--host", "::", "--port", "8080"]
