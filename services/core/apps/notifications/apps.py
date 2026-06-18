"""
Django AppConfig for the notifications application.

Registered as 'apps.notifications' with label 'notifications'.
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notifications"
