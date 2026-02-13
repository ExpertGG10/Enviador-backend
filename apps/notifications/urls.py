"""URLs da app de Notificações."""

from django.urls import path
from .views import (
    WhatsAppTestView,
    whatsapp_webhook_view,
    whatsapp_webhook_verify_view
)

app_name = 'notifications'

urlpatterns = [
    path('whatsapp/test/', WhatsAppTestView.as_view(), name='whatsapp-test'),
    path('whatsapp/webhook/', whatsapp_webhook_view, name='whatsapp-webhook'),
    path('whatsapp/webhook/verify/', whatsapp_webhook_verify_view, name='whatsapp-webhook-verify'),
]
