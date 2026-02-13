"""Testes da app de Destinatários."""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Recipient, RecipientGroup


class RecipientModelTests(TestCase):
    """Testes do modelo Recipient."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_recipient(self):
        """Teste de criação de destinatário."""
        recipient = Recipient.objects.create(
            user=self.user,
            email='recipient@example.com',
            name='Test Recipient'
        )
        self.assertEqual(recipient.user, self.user)
        self.assertEqual(recipient.email, 'recipient@example.com')


class RecipientGroupModelTests(TestCase):
    """Testes do modelo RecipientGroup."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.recipient = Recipient.objects.create(
            user=self.user,
            email='recipient@example.com'
        )
    
    def test_create_group(self):
        """Teste de criação de grupo."""
        group = RecipientGroup.objects.create(
            user=self.user,
            name='Test Group'
        )
        group.recipients.add(self.recipient)
        
        self.assertEqual(group.user, self.user)
        self.assertEqual(group.recipients.count(), 1)
