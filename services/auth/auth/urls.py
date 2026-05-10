from django.contrib import admin
from django.urls import include, path

from apps.authentication.jwks import JWKSView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/auth/', include('api_keys.urls')),
    path('.well-known/jwks.json', JWKSView.as_view(), name='jwks'),
    # path('health/', include('health_check.urls')),  # For KRV-003
]