"""Modelos da app de Destinatários."""

from django.db import models
from django.contrib.auth.models import User


class Recipient(models.Model):
    """Modelo para contatos individuais."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipients',
        help_text='Usuário proprietário'
    )
    email = models.EmailField(help_text='Email do destinatário')
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Nome do destinatário'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'email')
        ordering = ['name', 'email']
        verbose_name = 'Destinatário'
        verbose_name_plural = 'Destinatários'
        indexes = [
            models.Index(fields=['user', 'email']),
        ]
    
    def __str__(self):
        return f"{self.name or self.email}"


class RecipientGroup(models.Model):
    """Modelo para grupos de contatos."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipient_groups',
        help_text='Usuário proprietário'
    )
    name = models.CharField(
        max_length=255,
        help_text='Nome do grupo'
    )
    recipients = models.ManyToManyField(
        Recipient,
        related_name='groups',
        blank=True,
        help_text='Destinatários no grupo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
        verbose_name = 'Grupo de Destinatários'
        verbose_name_plural = 'Grupos de Destinatários'
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.recipients.count()} contatos)"
