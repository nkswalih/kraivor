from django.urls import path

from .github_app.views import (
    GitHubAppInstallationImportView,
    GitHubAppInstallationListView,
    GitHubAppInstallationRefreshView,
    GitHubAppInstallationRemoveView,
    GitHubAppInstallInitiateView,
)
from .views.repositories import (
    GitHubRepoSearchView,
    RepositoryDetailView,
    RepositoryListView,
)

urlpatterns = [
    path(
        "workspaces/<str:workspace_pk>/repos/github/",
        GitHubRepoSearchView.as_view(),
        name="workspace-github-repo-search",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/github/install/",
        GitHubAppInstallInitiateView.as_view(),
        name="workspace-github-app-install",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/github/installations/",
        GitHubAppInstallationListView.as_view(),
        name="workspace-github-app-installations",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/github/installations/<int:installation_pk>/refresh/",
        GitHubAppInstallationRefreshView.as_view(),
        name="workspace-github-app-installation-refresh",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/github/installations/<int:installation_pk>/",
        GitHubAppInstallationRemoveView.as_view(),
        name="workspace-github-app-installation-remove",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/github/installations/import/",
        GitHubAppInstallationImportView.as_view(),
        name="workspace-github-app-installation-import",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/",
        RepositoryListView.as_view(),
        name="workspace-repository-list",
    ),
    path(
        "workspaces/<str:workspace_pk>/repos/<uuid:repo_id>/",
        RepositoryDetailView.as_view(),
        name="workspace-repository-detail",
    ),
]
