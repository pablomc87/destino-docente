# Legacy Heroku entrypoint. Production uses the container image + Helm (see docs/DEPLOYMENT.md).
web: gunicorn config.wsgi
release: python manage.py migrate