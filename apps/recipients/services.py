"""Serviços da app de Destinatários."""

from django.db.models import Q, Count
from .models import Recipient, RecipientGroup


class RecipientService:
    """Serviço de gerenciamento de destinatários."""
    
    @staticmethod
    def get_user_recipients(user):
        """Obter todos os destinatários do usuário."""
        return Recipient.objects.filter(user=user)
    
    @staticmethod
    def create_recipient(user, email, name=''):
        """Criar novo destinatário."""
        recipient, created = Recipient.objects.get_or_create(
            user=user,
            email=email,
            defaults={'name': name}
        )
        return recipient, created
    
    @staticmethod
    def search_recipients(user, query):
        """Buscar destinatários por email ou nome."""
        return Recipient.objects.filter(
            user=user
        ).filter(
            Q(email__icontains=query) | Q(name__icontains=query)
        )
    
    @staticmethod
    def bulk_create_recipients(user, recipients_data):
        """
        Criar múltiplos destinatários em massa.
        
        Args:
            user: Usuário proprietário
            recipients_data: List[{'email': str, 'name': str}]
        
        Returns:
            List de recipients criados
        """
        recipients = []
        for data in recipients_data:
            recipient, _ = Recipient.objects.get_or_create(
                user=user,
                email=data.get('email'),
                defaults={'name': data.get('name', '')}
            )
            recipients.append(recipient)
        return recipients
    
    @staticmethod
    def delete_recipient(recipient):
        """Deletar destinatário."""
        recipient.delete()


class RecipientGroupService:
    """Serviço de gerenciamento de grupos de destinatários."""
    
    @staticmethod
    def get_user_groups(user):
        """Obter todos os grupos do usuário."""
        return RecipientGroup.objects.filter(user=user).annotate(
            count=Count('recipients')
        )
    
    @staticmethod
    def create_group(user, name, recipient_ids=None):
        """
        Criar novo grupo.
        
        Args:
            user: Usuário proprietário
            name: Nome do grupo
            recipient_ids: List de IDs de destinatários
        
        Returns:
            RecipientGroup instance
        """
        group = RecipientGroup.objects.create(user=user, name=name)
        
        if recipient_ids:
            recipients = Recipient.objects.filter(
                user=user,
                id__in=recipient_ids
            )
            group.recipients.set(recipients)
        
        return group
    
    @staticmethod
    def update_group(group, name=None, recipient_ids=None):
        """Atualizar grupo."""
        if name:
            group.name = name
        
        if recipient_ids is not None:
            recipients = Recipient.objects.filter(
                user=group.user,
                id__in=recipient_ids
            )
            group.recipients.set(recipients)
        
        group.save()
        return group
    
    @staticmethod
    def delete_group(group):
        """Deletar grupo."""
        group.delete()
    
    @staticmethod
    def add_recipients_to_group(group, recipient_ids):
        """Adicionar destinatários a um grupo."""
        recipients = Recipient.objects.filter(
            user=group.user,
            id__in=recipient_ids
        )
        group.recipients.add(*recipients)
    
    @staticmethod
    def remove_recipients_from_group(group, recipient_ids):
        """Remover destinatários de um grupo."""
        group.recipients.filter(id__in=recipient_ids).delete()
