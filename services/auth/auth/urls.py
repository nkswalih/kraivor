from authentication.jwks import JWKSView
from authentication.oauth.token import GitHubOAuthTokenView
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health_check(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/auth/", include("authentication.urls")),
    path("api/auth/", include("api_keys.urls")),
    path("api/profiles/", include("profiles.urls")),
    # Internal service-to-service: retrieve a user's stored GitHub OAuth token
    path("api/oauth/github/token/", GitHubOAuthTokenView.as_view(), name="github-oauth-token"),
    path(".well-known/jwks.json", JWKSView.as_view(), name="jwks"),
    path("api/health/", health_check, name="health"),
    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
