from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    """Serializer para dados do usuário."""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de novo usuário."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Confirmar Senha'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate(self, data):
        """Validar que as senhas coincidem."""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                'password2': 'As senhas não coincidem.'
            })
        return data
    
    def create(self, validated_data):
        """Criar novo usuário."""
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer para login do usuário."""
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Autenticar usuário."""
        user = authenticate(
            username=data.get('username'),
            password=data.get('password')
        )
        
        if not user:
            raise serializers.ValidationError(
                'Credenciais inválidas. Verifique seu usuário e senha.'
            )
        
        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para mudança de senha."""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password2 = serializers.CharField(write_only=True, required=True)
    
    def validate(self, data):
        """Validar senhas."""
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({
                'new_password2': 'As novas senhas não coincidem.'
            })
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({
                'new_password': 'A nova senha deve ter pelo menos 8 caracteres.'
            })
        return data


# Email Models Serializers
from .models import Sender, Recipient, RecipientGroup, EmailLog
from .validators import validate_email


class SenderSerializer(serializers.ModelSerializer):
    """Serializer para contas de email remetente."""
    
    class Meta:
        model = Sender
        fields = ('id', 'email', 'name', 'is_active', 'is_default', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def validate_email(self, value):
        if not validate_email(value):
            raise serializers.ValidationError("Email inválido")
        return value


class RecipientSerializer(serializers.ModelSerializer):
    """Serializer para contatos individuais."""
    
    class Meta:
        model = Recipient
        fields = ('id', 'email', 'name', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def validate_email(self, value):
        if not validate_email(value):
            raise serializers.ValidationError("Email inválido")
        return value


class RecipientGroupSerializer(serializers.ModelSerializer):
    """Serializer para grupos de contatos."""
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RecipientGroup
        fields = ('id', 'name', 'recipient_count', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer para histórico de envios."""
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = ('id', 'recipient_email', 'subject', 'status', 'attempts', 'error_message', 'sender_email', 'sent_at', 'created_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
