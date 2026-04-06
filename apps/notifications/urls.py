"""URLs da app de Notificações."""

from django.urls import path
from .views import (
    WhatsAppTestView,
    whatsapp_webhook_view,
    whatsapp_webhook_verify_view,
    whatsapp_inbox_view,
    whatsapp_send_text_view,
    whatsapp_media_access_view,
)

app_name = 'notifications'

urlpatterns = [
    path('whatsapp/test/', WhatsAppTestView.as_view(), name='whatsapp-test'),
    path('whatsapp/webhook/', whatsapp_webhook_view, name='whatsapp-webhook'),
    path('whatsapp/webhook/verify/', whatsapp_webhook_verify_view, name='whatsapp-webhook-verify'),
    path('whatsapp/inbox/', whatsapp_inbox_view, name='whatsapp-inbox'),
    path('whatsapp/media/<int:asset_id>/', whatsapp_media_access_view, name='whatsapp-media-access'),
    path('whatsapp/send-text/', whatsapp_send_text_view, name='whatsapp-send-text'),
]
