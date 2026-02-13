"""Serializers da app de Autenticação."""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


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
    
    def validate_username(self, value):
        """Verificar se username já existe."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Este nome de usuário já está registrado.'
            )
        return value
    
    def validate_email(self, value):
        """Verificar se email já está registrado e se é válido."""
        if not value:
            raise serializers.ValidationError(
                'O email é obrigatório.'
            )
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Este email já está registrado.'
            )
        return value
    
    def validate_password(self, value):
        """Validar senha contra as regras do Django."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
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
