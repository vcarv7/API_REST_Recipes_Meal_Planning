"""Ajustes de desarrollo."""

from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = config('DEBUG', default=True, cast=bool)

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
