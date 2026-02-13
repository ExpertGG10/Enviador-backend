"""Configuração da app de Destinatários."""

from django.apps import AppConfig


class RecipientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recipients'
    verbose_name = 'Gerenciamento de Destinatários'
