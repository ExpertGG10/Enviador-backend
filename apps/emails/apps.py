"""Configuração da app de Emails."""

from django.apps import AppConfig


class EmailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.emails'
    verbose_name = 'Envio e Histórico de Emails'
