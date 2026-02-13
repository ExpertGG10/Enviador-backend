"""Serializers da app de Remetentes."""

from rest_framework import serializers
from .models import Sender, AppPassword


class SenderSerializer(serializers.ModelSerializer):
    """Serializer para contas de email remetente."""
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    
    class Meta:
        model = Sender
        fields = ('id', 'email', 'name', 'is_active', 'is_default', 'smtp_host', 'smtp_port', 'user_username', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_email(self, value):
        """Validar formato de email."""
        if not value or '@' not in value:
            raise serializers.ValidationError("Email inválido")
        return value


class SenderCreateSerializer(serializers.ModelSerializer):
    """Serializer para criar nova conta remetente."""
    
    class Meta:
        model = Sender
        fields = ('email', 'name', 'is_active', 'is_default', 'smtp_host', 'smtp_port')


class AppPasswordSerializer(serializers.ModelSerializer):
    """Serializer para senha de aplicativo (apenas metadata, não expõe a senha)."""
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    
    class Meta:
        model = AppPassword
        fields = ('id', 'sender_email', 'crypto_scheme', 'key_id', 'created_at', 'updated_at')
        read_only_fields = ('id', 'crypto_scheme', 'key_id', 'created_at', 'updated_at', 'ciphertext')


class AppPasswordCreateSerializer(serializers.Serializer):
    """Serializer para criar/atualizar senha de aplicativo."""
    sender_id = serializers.IntegerField()
    app_password = serializers.CharField(
        write_only=True,
        help_text='Senha de aplicativo em texto plano (será criptografada)'
    )
    
    def validate_app_password(self, value):
        """Validar que a senha não está vazia."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Senha não pode estar vazia")
        return value
