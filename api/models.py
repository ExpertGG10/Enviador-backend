"""
Django Models para o sistema de email.
"""
from django.db import models
from django.contrib.auth.models import User


class Sender(models.Model):
    """Modelo para contas de email remetente."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_senders')
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'email')
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.name or self.email} ({self.user.username})"


class Recipient(models.Model):
    """Modelo para contatos individuais."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipients')
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'email')
        ordering = ['name', 'email']
    
    def __str__(self):
        return f"{self.name or self.email}"


class RecipientGroup(models.Model):
    """Modelo para grupos de contatos."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipient_groups')
    name = models.CharField(max_length=255)
    recipients = models.ManyToManyField(Recipient, related_name='groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.recipients.count()} contatos)"


class EmailLog(models.Model):
    """Modelo para registrar histórico de envios."""
    STATUS_CHOICES = [
        ('queued', 'Enfileirado'),
        ('sending', 'Enviando'),
        ('sent', 'Enviado'),
        ('failed', 'Falhou'),
        ('skipped', 'Pulado'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_logs')
    sender = models.ForeignKey(Sender, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['sender', 'status']),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.recipient_email} - {self.subject[:50]}"
