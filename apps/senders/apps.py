"""Configuração da app de Remetentes."""

from django.apps import AppConfig


class SendersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.senders'
    verbose_name = 'Gerenciamento de Remetentes'
