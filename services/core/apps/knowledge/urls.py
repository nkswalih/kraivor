"""
URL configuration for the knowledge app — KRV-022.

All routes are mounted under the api/ prefix in core/urls.py.
The /workspace/ segment visible in the ticket spec is an nginx/gateway prefix.

Full Django-level paths (under the api/ mount):

  Workspace-scoped (list + create):
    GET  workspaces/<workspace_pk>/knowledge/          list knowledge spaces
    POST workspaces/<workspace_pk>/knowledge/          create a knowledge space

  Resource-scoped (retrieve + update + delete):
    GET    knowledge/<pk>/                             retrieve a knowledge space
    PUT    knowledge/<pk>/                             update a knowledge space
    DELETE knowledge/<pk>/                             delete a knowledge space

URL design decisions:
  - workspace_pk follows the same naming convention as repositories/members —
    the outer workspace PK is always workspace_pk.
  - pk is the knowledge space UUID for detail operations.
  - Detail endpoints are NOT nested under /workspaces/ because the client
    holds the knowledge space UUID after list/create and does not need to
    re-specify the workspace. The view enforces membership internally.
"""

from django.urls import path

from .views import KnowledgeSpaceDetailView, KnowledgeSpaceListCreateView

urlpatterns = [
    # Workspace-scoped: list + create
    path(
        "workspaces/<uuid:workspace_pk>/knowledge/",
        KnowledgeSpaceListCreateView.as_view(),
        name="workspace-knowledge-list",
    ),
    # Resource-scoped: retrieve + update + delete
    path(
        "knowledge/<uuid:pk>/",
        KnowledgeSpaceDetailView.as_view(),
        name="knowledge-detail",
    ),
]
