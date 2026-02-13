"""Serializers da app de Destinatários."""

from rest_framework import serializers
from .models import Recipient, RecipientGroup


class RecipientSerializer(serializers.ModelSerializer):
    """Serializer para contatos individuais."""
    
    class Meta:
        model = Recipient
        fields = ('id', 'email', 'name', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def validate_email(self, value):
        """Validar formato de email."""
        if not value or '@' not in value:
            raise serializers.ValidationError("Email inválido")
        return value


class RecipientGroupSerializer(serializers.ModelSerializer):
    """Serializer para grupos de contatos."""
    recipient_count = serializers.SerializerMethodField()
    recipients = RecipientSerializer(many=True, read_only=True)
    
    class Meta:
        model = RecipientGroup
        fields = ('id', 'name', 'recipient_count', 'recipients', 'created_at')
        read_only_fields = ('id', 'created_at', 'recipients')
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()


class RecipientGroupCreateSerializer(serializers.ModelSerializer):
    """Serializer para criar/atualizar grupos."""
    recipient_ids = serializers.PrimaryKeyRelatedField(
        queryset=Recipient.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = RecipientGroup
        fields = ('name', 'recipient_ids')
