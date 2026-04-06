"""URLs da aba Conta."""

from django.urls import path
from .views import (
    AccountSettingsView,
    GmailSenderListCreateView,
    GmailSenderDetailView,
    GmailTemplateListCreateView,
    GmailTemplateDetailView,
    WhatsAppSenderListCreateView,
    WhatsAppSenderDetailView,
    WhatsAppTemplateListCreateView,
    WhatsAppTemplateDetailView,
    WhatsAppTemplatePreviewView,
)

urlpatterns = [
    path('settings/', AccountSettingsView.as_view(), name='account-settings'),
    path('gmail/senders/', GmailSenderListCreateView.as_view(), name='gmail-sender-list-create'),
    path('gmail/senders/<uuid:sender_id>/', GmailSenderDetailView.as_view(), name='gmail-sender-detail'),
    path('gmail/senders/<uuid:sender_id>/templates/', GmailTemplateListCreateView.as_view(), name='gmail-template-list-create'),
    path('gmail/senders/<uuid:sender_id>/templates/<uuid:template_id>/', GmailTemplateDetailView.as_view(), name='gmail-template-detail'),
    path('whatsapp/senders/', WhatsAppSenderListCreateView.as_view(), name='whatsapp-sender-list-create'),
    path('whatsapp/senders/<uuid:sender_id>/', WhatsAppSenderDetailView.as_view(), name='whatsapp-sender-detail'),
    path('whatsapp/senders/<uuid:sender_id>/templates/', WhatsAppTemplateListCreateView.as_view(), name='whatsapp-template-list-create'),
    path('whatsapp/senders/<uuid:sender_id>/templates/<uuid:template_id>/', WhatsAppTemplateDetailView.as_view(), name='whatsapp-template-detail'),
    path('whatsapp/senders/<uuid:sender_id>/templates/<str:template_name>/preview/', WhatsAppTemplatePreviewView.as_view(), name='whatsapp-template-preview'),
]
