from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.repositories.github_app.views import GitHubAppInstallCallbackView
from apps.repositories.github_app.webhook import github_app_webhook
from apps.repositories.views import GitHubOAuthConnectView


def health_check(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health"),
    path("api/", include("apps.workspaces.urls")),
    path("api/", include("apps.repositories.urls")),
    path("api/", include("apps.knowledge.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.chat.urls")),
    path(
        "api/oauth/github/connect/",
        GitHubOAuthConnectView.as_view(),
        name="github-oauth-connect",
    ),
    path(
        "api/github-app/callback/",
        GitHubAppInstallCallbackView.as_view(),
        name="github-app-install-callback",
    ),
    path("api/github-app/webhook/", github_app_webhook, name="github-app-webhook"),
]
