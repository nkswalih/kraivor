"""
URL configuration for the repositories app — KRV-021.

All routes are nested under the workspaces/ prefix (mounted at api/ in core/urls.py).
The /workspace/ segment visible in the ticket spec is an nginx/gateway prefix.

Full Django-level paths (under the api/ mount):

  Repository management (KRV-021):
    GET    workspaces/{workspace_pk}/repos/             list connected repositories
    POST   workspaces/{workspace_pk}/repos/             connect a repository
    DELETE workspaces/{workspace_pk}/repos/{repo_id}/   disconnect a repository

URL design decisions:
  - workspace_pk follows the same naming convention as member management in
    workspaces/urls.py — the outer workspace PK is always workspace_pk
  - repo_id is the Kraivor repository UUID (not the GitHub repo ID)
  - No retrieve (GET /repos/{id}/) endpoint is required by KRV-021; list returns
    all repos and includes full metadata for each
"""

from django.urls import path

from .views import RepositoryDetailView, RepositoryView

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_pk>/repos/",
        RepositoryView.as_view(),
        name="workspace-repository-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/repos/<uuid:repo_id>/",
        RepositoryDetailView.as_view(),
        name="workspace-repository-detail",
    ),
]
