# Content Orchestrator worker — production-style image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home /app --shell /usr/sbin/nologin app

COPY pyproject.toml ./
COPY worker ./worker

RUN pip install --upgrade pip \
    && pip install . \
    && chown -R app:app /app

USER app

CMD ["python", "-m", "worker.main"]
