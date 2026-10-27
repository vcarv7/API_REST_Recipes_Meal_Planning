"""Ajustes de produccion: seguridad activa, todo lo demas por entorno."""

from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False

# HTTPS / cookies
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # una semana
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# El PaaS termina el TLS en su proxy: Django debe leer el esquema original.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Estaticos (collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Manifiesto + compresion; los sirve whitenoise desde STATIC_ROOT
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

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

# Origenes confiables para CSRF (admin/sesion detras del proxy HTTPS del PaaS)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Logs a stdout: la plataforma los captura
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
