from .base import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kraivor_dev',
        'USER': 'kraivor',
        'PASSWORD': 'kraivor',
        'HOST': 'postgres',
        'PORT': '5432',
    }
}