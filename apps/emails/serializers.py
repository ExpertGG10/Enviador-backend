"""Serializers da app de Emails."""

from rest_framework import serializers
from .models import EmailLog


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer para histórico de envios."""
    sender_email = serializers.CharField(
        source='sender.email',
        read_only=True
    )
    sender_name = serializers.CharField(
        source='sender.name',
        read_only=True
    )
    
    class Meta:
        model = EmailLog
        fields = (
            'id', 'recipient_email', 'subject', 'status', 'attempts',
            'error_message', 'sender_email', 'sender_name', 'sent_at',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'sent_at', 'sender_email', 'sender_name'
        )
