"""Serviços da app de Remetentes."""

from django.db.models import Q
from .models import Sender, AppPassword
from shared.utils.crypto import encrypt_password, decrypt_password
import logging

logger = logging.getLogger(__name__)


class SenderService:
    """Serviço de gerenciamento de contas remetentes."""
    
    @staticmethod
    def get_user_senders(user):
        """Obter todas as contas remetentes do usuário."""
        return Sender.objects.filter(user=user).order_by('-is_default', '-created_at')
    
    @staticmethod
    def get_default_sender(user):
        """Obter conta remetente padrão do usuário."""
        return Sender.objects.filter(user=user, is_default=True).first()
    
    @staticmethod
    def get_active_senders(user):
        """Obter contas remetentes ativas do usuário."""
        return Sender.objects.filter(user=user, is_active=True)
    
    @staticmethod
    def create_sender(user, email, name='', is_active=True, is_default=False, smtp_host='smtp.gmail.com', smtp_port=465):
        """
        Criar nova conta remetente.
        
        Args:
            user: Usuário proprietário
            email: Email da conta
            name: Nome de exibição
            is_active: Se está ativa
            is_default: Se deve ser padrão
            smtp_host: Host SMTP
            smtp_port: Porta SMTP
        
        Returns:
            Sender object
        """
        # Se for padrão, desmarcar os outros
        if is_default:
            Sender.objects.filter(user=user).update(is_default=False)
        
        sender, created = Sender.objects.get_or_create(
            user=user,
            email=email,
            defaults={
                'name': name,
                'is_active': is_active,
                'is_default': is_default,
                'smtp_host': smtp_host,
                'smtp_port': smtp_port
            }
        )
        return sender
    
    @staticmethod
    def update_sender(sender, **kwargs):
        """Atualizar dados da conta remetente."""
        for key, value in kwargs.items():
            if hasattr(sender, key) and key not in ['id', 'user', 'created_at', 'updated_at']:
                setattr(sender, key, value)
        sender.save()
        return sender
    
    @staticmethod
    def delete_sender(sender):
        """Deletar conta remetente (e sua senha)."""
        # Deletar senha associada
        AppPassword.objects.filter(sender=sender).delete()
        sender.delete()
    
    @staticmethod
    def search_senders(user, query):
        """Buscar contas remetentes por email ou nome."""
        return Sender.objects.filter(
            user=user
        ).filter(
            Q(email__icontains=query) | Q(name__icontains=query)
        )


class AppPasswordService:
    """Serviço para gerenciar senhas de aplicativo criptografadas."""
    
    @staticmethod
    def set_app_password(sender, plain_password):
        """
        Definir/atualizar senha de aplicativo para uma conta.
        
        Args:
            sender: Objeto Sender
            plain_password: Senha em texto plano
        
        Returns:
            AppPassword object
        """
        try:
            # Criptografar a senha
            encrypted = encrypt_password(plain_password)
            
            # Criar ou atualizar registro
            app_password, created = AppPassword.objects.get_or_create(
                sender=sender,
                defaults={
                    'ciphertext': encrypted,
                    'crypto_scheme': 'fernet:v1',
                    'key_id': 'enviador-v1'
                }
            )
            
            if not created:
                app_password.ciphertext = encrypted
                app_password.save()
            
            logger.info(f"Senha de aplicativo definida para {sender.email}")
            return app_password
        
        except Exception as e:
            logger.error(f"Erro ao definir senha de aplicativo: {str(e)}")
            raise
    
    @staticmethod
    def get_app_password(sender) -> str:
        """
        Obter senha de aplicativo descriptografada.
        
        Args:
            sender: Objeto Sender
        
        Returns:
            str: Senha em texto plano
        """
        try:
            app_password = AppPassword.objects.get(sender=sender)
            
            # Descriptografar
            plain = decrypt_password(
                app_password.ciphertext,
                app_password.crypto_scheme,
                app_password.key_id
            )
            
            logger.debug(f"Senha de aplicativo descriptografada para {sender.email}")
            return plain
        
        except AppPassword.DoesNotExist:
            logger.error(f"Nenhuma senha de aplicativo para {sender.email}")
            raise ValueError(f"Nenhuma senha de aplicativo configurada para {sender.email}")
        
        except Exception as e:
            logger.error(f"Erro ao descriptografar senha: {str(e)}")
            raise
    
    @staticmethod
    def has_app_password(sender) -> bool:
        """Verificar se uma conta tem senha de aplicativo configurada."""
        return AppPassword.objects.filter(sender=sender).exists()
    
    @staticmethod
    def delete_app_password(sender):
        """Deletar senha de aplicativo."""
        AppPassword.objects.filter(sender=sender).delete()
        logger.info(f"Senha de aplicativo deletada para {sender.email}")
