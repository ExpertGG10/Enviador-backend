"""URLs principais do projeto Enviador."""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_health(request):
    """Health check do root."""
    return JsonResponse({'status': 'ok', 'service': 'Enviador API'})


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Health check
    path('', root_health),
    
    # API URLs (send, health checks, etc) - Include all api.* views
    path('api/', include('api.urls')),
    
    # API v1 URLs
    path('api/auth/', include('apps.auth_app.urls')),
    path('api/senders/', include('apps.senders.urls')),
    path('api/recipients/', include('apps.recipients.urls')),
    path('api/emails/', include('apps.emails.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
]
