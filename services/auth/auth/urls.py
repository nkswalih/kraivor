from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/auth/', include('api_keys.urls')),
    # path('health/', include('health_check.urls')),  # For KRV-003
]