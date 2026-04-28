# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /wheels
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache --no-index --find-links=/wheels/ -r /wheels/requirements.txt

COPY manage.py pyproject.toml ./
COPY config ./config
COPY apps ./apps
COPY templates ./templates
COPY static ./static

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
