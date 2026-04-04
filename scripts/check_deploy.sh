#!/usr/bin/env bash
# Run Django deploy checks with production-like security settings (no DB connection required).
# Usage: from repo root, `./scripts/check_deploy.sh`
# For daily development use `python manage.py check` without --deploy.

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi

export ENVIRONMENT=production
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$($PY -c 'import secrets; print(secrets.token_urlsafe(64))')}"
export DATABASE_URL="${DATABASE_URL:-postgresql://deploy_check:deploy_check@127.0.0.1:5432/deploy_check}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-destino-docente.org,www.destino-docente.org,localhost,127.0.0.1}"
export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-https://destino-docente.org,https://www.destino-docente.org}"
export TRUST_BEHIND_PROXY="${TRUST_BEHIND_PROXY:-true}"
export SECURE_SSL_REDIRECT="${SECURE_SSL_REDIRECT:-false}"
export SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-true}"
export CSRF_COOKIE_SECURE="${CSRF_COOKIE_SECURE:-true}"

exec "$PY" manage.py check --deploy "$@"
