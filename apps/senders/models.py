"""Modelos da app de Remetentes."""

from django.db import models
from django.contrib.auth.models import User


class Sender(models.Model):
    """Modelo para contas de email remetente."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_senders',
        help_text='Usuário proprietário desta conta remetente'
    )
    email = models.EmailField(help_text='Email da conta remetente')
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Nome de exibição (ex: João Silva)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Indica se a conta está ativa para envios'
    )
    is_default = models.BooleanField(
        default=False,
        help_text='Define como remetente padrão do usuário'
    )
    smtp_host = models.CharField(
        max_length=255,
        default='smtp.gmail.com',
        help_text='Host SMTP do provedor de email'
    )
    smtp_port = models.IntegerField(
        default=465,
        help_text='Porta SMTP (465 para SSL, 587 para TLS)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'email')
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Remetente'
        verbose_name_plural = 'Remetentes'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', '-is_default']),
        ]
    
    def __str__(self):
        return f"{self.name or self.email} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        """Se marcar como padrão, desmarcar os outros."""
        if self.is_default:
            Sender.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class AppPassword(models.Model):
    """Modelo para senhas de aplicativo criptografadas (adaptado do desktop app)."""
    SCHEME_CHOICES = [
        ('fernet:v1', 'Fernet v1'),
        ('plain', 'Plano (não seguro)'),
    ]
    
    sender = models.OneToOneField(
        Sender,
        on_delete=models.CASCADE,
        related_name='app_password',
        help_text='Conta remetente associada'
    )
    
    # Senha criptografada
    ciphertext = models.TextField(
        help_text='Senha criptografada (token Fernet)'
    )
    
    # Informações de criptografia
    crypto_scheme = models.CharField(
        max_length=20,
        choices=SCHEME_CHOICES,
        default='fernet:v1',
        help_text='Esquema de criptografia usado'
    )
    
    key_id = models.CharField(
        max_length=50,
        default='enviador-v1',
        help_text='Identificador da chave de criptografia'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Senha de Aplicativo'
        verbose_name_plural = 'Senhas de Aplicativo'
    
    def __str__(self):
        return f"App Password para {self.sender.email}"
