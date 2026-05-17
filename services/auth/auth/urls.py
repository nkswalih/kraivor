from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.authentication.jwks import JWKSView


def health_check(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/auth/', include('api_keys.urls')),
    path('.well-known/jwks.json', JWKSView.as_view(), name='jwks'),
    path('api/health/', health_check, name='health'),
]