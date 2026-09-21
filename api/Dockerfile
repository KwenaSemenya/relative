FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8080
# Bind 0.0.0.0, not ::. Traffic arrives through the Fly proxy on .flycast and
# the proxy connects over IPv4. Uvicorn's :: bind is IPv6-only — it refuses
# IPv4 rather than accepting mapped addresses — so :: makes the proxy report
# "instance refused connection" and the API becomes unreachable.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
