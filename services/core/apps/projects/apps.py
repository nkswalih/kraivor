"""Django AppConfig for the projects application."""
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Registers the projects app with Django under the ``projects`` label."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    label = "projects"
    verbose_name = "Projects"
