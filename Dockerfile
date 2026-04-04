# Production image: collectstatic at build (dev DB settings), run gunicorn at runtime.
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt

COPY . .
ENV DJANGO_SETTINGS_MODULE=config.settings
# Must match production STORAGES (Manifest + WhiteNoise). With ENVIRONMENT=development,
# collectstatic uses plain StaticFilesStorage and no staticfiles.json → runtime 500 on {% static %}.
ENV ENVIRONMENT=production
ENV DJANGO_SECRET_KEY=docker-build-collectstatic-only-not-used-at-runtime-0123456789abcdef
ENV DATABASE_URL=postgresql://collectstatic:collectstatic@127.0.0.1:5432/collectstatic
ENV ALLOWED_HOSTS=localhost,127.0.0.1
RUN python manage.py collectstatic --noinput

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

ENV PATH=/root/.local/bin:$PATH
ENV DJANGO_SETTINGS_MODULE=config.settings

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
