from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "healthy"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health'),
    path('api/', include('apps.workspaces.urls')),
    path('api/', include('apps.repositories.urls')),
    path('api/', include('apps.knowledge.urls')),
    path('api/', include('apps.notifications.urls')),
]