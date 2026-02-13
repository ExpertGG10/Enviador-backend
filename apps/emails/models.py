"""Modelos da app de Emails."""

from django.db import models
from django.contrib.auth.models import User
from apps.senders.models import Sender
from shared.constants import EMAIL_STATUS_CHOICES


class EmailLog(models.Model):
    """Modelo para registrar histórico de envios de email."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_logs',
        help_text='Usuário que enviou'
    )
    sender = models.ForeignKey(
        Sender,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        help_text='Conta remetente usada'
    )
    recipient_email = models.EmailField(help_text='Email do destinatário')
    subject = models.CharField(max_length=255, help_text='Assunto do email')
    status = models.CharField(
        max_length=20,
        choices=EMAIL_STATUS_CHOICES,
        default='queued',
        help_text='Status do envio'
    )
    attempts = models.IntegerField(
        default=0,
        help_text='Número de tentativas de envio'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Mensagem de erro, se houver'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Quando foi enviado com sucesso'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Histórico de Email'
        verbose_name_plural = 'Histórico de Emails'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.recipient_email} - {self.subject[:50]}"
