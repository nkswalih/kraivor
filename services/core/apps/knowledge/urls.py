from django.urls import path

from .views import (
    KnowledgeAssetDetailView,
    KnowledgeAssetListCreateView,
    KnowledgeSpaceDetailView,
    KnowledgeSpaceListCreateView,
)

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_pk>/knowledge/",
        KnowledgeSpaceListCreateView.as_view(),
        name="workspace-knowledge-list",
    ),
    path(
        "knowledge/<uuid:pk>/",
        KnowledgeSpaceDetailView.as_view(),
        name="knowledge-detail",
    ),
    path(
        "knowledge/<uuid:knowledge_pk>/assets/",
        KnowledgeAssetListCreateView.as_view(),
        name="knowledge-asset-list",
    ),
    path(
        "knowledge/<uuid:knowledge_pk>/assets/<uuid:pk>/",
        KnowledgeAssetDetailView.as_view(),
        name="knowledge-asset-detail",
    ),
]
