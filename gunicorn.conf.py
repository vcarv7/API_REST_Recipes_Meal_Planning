"""Configuracion de gunicorn para el PaaS (Railway y similares)."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get('WEB_CONCURRENCY', '3'))
timeout = 30
accesslog = '-'
errorlog = '-'
loglevel = 'info'
