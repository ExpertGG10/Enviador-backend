"""Serviços de Autenticação."""

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class AuthService:
    """Serviço de autenticação."""
    
    @staticmethod
    def register_user(username, email, password, first_name='', last_name=''):
        """
        Registrar novo usuário.
        
        Args:
            username: Nome de usuário único
            email: Email único
            password: Senha
            first_name: Primeiro nome
            last_name: Último nome
            
        Returns:
            Tuple (user, token)
        """
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        token, _ = Token.objects.get_or_create(user=user)
        return user, token
    
    @staticmethod
    def get_or_create_token(user):
        """Obter ou criar token para usuário."""
        token, _ = Token.objects.get_or_create(user=user)
        return token
    
    @staticmethod
    def delete_token(user):
        """Deletar token do usuário (logout)."""
        try:
            user.auth_token.delete()
            return True
        except:
            return False
    
    @staticmethod
    def change_password(user, new_password):
        """Alterar senha do usuário."""
        user.set_password(new_password)
        user.save()
        # Regenerar token após mudança de senha
        token, _ = Token.objects.get_or_create(user=user)
        return token
