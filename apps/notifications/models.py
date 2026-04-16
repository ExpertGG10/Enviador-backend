"""Modelos para persistencia de webhooks do WhatsApp."""

from django.db import models


class WhatsAppWebhookEvent(models.Model):
    """Payload bruto recebido no endpoint de webhook."""

    object_type = models.CharField(max_length=80)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'WhatsApp Webhook Event'
        verbose_name_plural = 'WhatsApp Webhook Events'

    def __str__(self):
        return f"{self.object_type} @ {self.received_at:%Y-%m-%d %H:%M:%S}"


class WhatsAppWebhookEntry(models.Model):
    """Bloco entry de um evento de webhook."""

    event = models.ForeignKey(
        WhatsAppWebhookEvent,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    entry_index = models.PositiveIntegerField()
    entry_id = models.CharField(max_length=120, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['id']
        verbose_name = 'WhatsApp Webhook Entry'
        verbose_name_plural = 'WhatsApp Webhook Entries'

    def __str__(self):
        return f"Entry {self.entry_index} ({self.entry_id or 'sem-id'})"


class WhatsAppWebhookChange(models.Model):
    """Bloco changes dentro de uma entry."""

    entry = models.ForeignKey(
        WhatsAppWebhookEntry,
        on_delete=models.CASCADE,
        related_name='changes',
    )
    change_index = models.PositiveIntegerField()
    field = models.CharField(max_length=80, blank=True)
    messaging_product = models.CharField(max_length=40, blank=True)
    display_phone_number = models.CharField(max_length=40, blank=True)
    phone_number_id = models.CharField(max_length=80, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['id']
        verbose_name = 'WhatsApp Webhook Change'
        verbose_name_plural = 'WhatsApp Webhook Changes'

    def __str__(self):
        return f"Change {self.change_index} ({self.field or 'sem-field'})"


class WhatsAppWebhookContact(models.Model):
    """Contato recebido no webhook."""

    change = models.ForeignKey(
        WhatsAppWebhookChange,
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    contact_index = models.PositiveIntegerField()
    wa_id = models.CharField(max_length=40, db_index=True)
    profile_name = models.CharField(max_length=160, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['id']
        verbose_name = 'WhatsApp Webhook Contact'
        verbose_name_plural = 'WhatsApp Webhook Contacts'

    def __str__(self):
        return f"{self.profile_name or 'Contato'} ({self.wa_id})"


class WhatsAppWebhookMessage(models.Model):
    """Mensagem recebida no webhook, com suporte a leitura visual futura."""

    change = models.ForeignKey(
        WhatsAppWebhookChange,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    message_index = models.PositiveIntegerField()
    whatsapp_message_id = models.CharField(max_length=255, db_index=True)
    from_wa_id = models.CharField(max_length=40, db_index=True)
    message_type = models.CharField(max_length=40)
    timestamp = models.BigIntegerField(null=True, blank=True)
    text_body = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Webhook Message'
        verbose_name_plural = 'WhatsApp Webhook Messages'

    def __str__(self):
        return f"{self.from_wa_id} -> {self.message_type} ({self.whatsapp_message_id})"


class WhatsAppOutboundMessage(models.Model):
    """Mensagem de texto enviada pelo sistema para um contato WhatsApp."""

    to_wa_id = models.CharField(max_length=40, db_index=True)
    text_body = models.TextField()
    whatsapp_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    phone_number_id = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=40, default='sent')
    sent_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='whatsapp_outbound_messages',
    )
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Outbound Message'
        verbose_name_plural = 'WhatsApp Outbound Messages'

    def __str__(self):
        return f"to {self.to_wa_id} ({self.whatsapp_message_id or 'pending-id'})"


class WhatsAppMediaAsset(models.Model):
    """Asset de mídia associado a uma mensagem WhatsApp (inbound/outbound)."""

    webhook_message = models.OneToOneField(
        WhatsAppWebhookMessage,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='media_asset',
    )
    whatsapp_message_id = models.CharField(max_length=255, db_index=True)
    media_id = models.CharField(max_length=255, blank=True, db_index=True)
    media_type = models.CharField(max_length=40, default='image')
    mime_type = models.CharField(max_length=120, blank=True)
    sha256 = models.CharField(max_length=128, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    file = models.FileField(upload_to='whatsapp/media/%Y/%m/%d/', blank=True)
    status = models.CharField(max_length=30, default='pending', db_index=True)
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Media Asset'
        verbose_name_plural = 'WhatsApp Media Assets'

    def __str__(self):
        return f"{self.media_type} ({self.whatsapp_message_id})"


class WhatsAppPendingAttachment(models.Model):
    """Anexo pendente aguardando clique de botao para envio ao contato."""

    sender = models.ForeignKey(
        'auth_app.WhatsAppSender',
        on_delete=models.CASCADE,
        related_name='pending_attachments',
    )
    wa_id = models.CharField(max_length=40, db_index=True)
    button_payload = models.CharField(max_length=255, db_index=True)
    media_type = models.CharField(max_length=40, default='document')
    mime_type = models.CharField(max_length=120, blank=True)
    caption = models.TextField(blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=128, blank=True, db_index=True)
    file = models.FileField(upload_to='whatsapp/pending/%Y/%m/%d/')
    status = models.CharField(max_length=30, default='pending', db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    trigger_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'wa_id', 'button_payload', 'status']),
            models.Index(fields=['sender', 'status', '-created_at']),
        ]
        verbose_name = 'WhatsApp Pending Attachment'
        verbose_name_plural = 'WhatsApp Pending Attachments'

    def __str__(self):
        return f"{self.wa_id} ({self.button_payload}) [{self.status}]"
