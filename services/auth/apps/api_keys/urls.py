"""
apps/api_keys/urls.py

Wired into config/urls.py as:
    path("api/auth/", include("api_keys.urls"))

Final routes:
    POST   /api/auth/api-keys/
    GET    /api/auth/api-keys/
    DELETE /api/auth/api-keys/<key_id>/
"""

from api_keys.views import APIKeyListCreateView, APIKeyRevokeView
from django.urls import path

urlpatterns = [
    path("api-keys/", APIKeyListCreateView.as_view(), name="api-key-list-create"),
    path("api-keys/<str:key_id>/", APIKeyRevokeView.as_view(), name="api-key-revoke"),
]
