"""Ajustes de produccion: seguridad activa, todo lo demas por entorno."""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# HTTPS / cookies
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # una semana
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Si el deploy va tras un proxy/load balancer que termina el TLS:
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Estaticos (collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Base de datos: conexiones persistentes con verificacion
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Email (en Django 6 la configuracion SMTP vive DENTRO de MAILERS;
# los viejos EMAIL_* estan prohibidos cuando MAILERS esta definido)
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': {
            'host': config('EMAIL_HOST', default=''),
            'port': config('EMAIL_PORT', default=587, cast=int),
            'username': config('EMAIL_HOST_USER', default=''),
            'password': config('EMAIL_HOST_PASSWORD', default=''),
            'use_tls': config('EMAIL_USE_TLS', default=True, cast=bool),
        },
    },
}
