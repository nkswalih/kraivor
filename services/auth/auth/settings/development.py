from .base import *

DEBUG = True

# Use localhost for local dev, can be overridden via DATABASE_URL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kraivor_dev',
        'USER': 'kraivor',
        'PASSWORD': 'kraivor',
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': '5432',
    }
}