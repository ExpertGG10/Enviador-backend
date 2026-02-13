"""Testes da app de Remetentes."""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Sender


class SenderModelTests(TestCase):
    """Testes do modelo Sender."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_sender(self):
        """Teste de criação de conta remetente."""
        sender = Sender.objects.create(
            user=self.user,
            email='sender@example.com',
            name='Test Sender'
        )
        self.assertEqual(sender.user, self.user)
        self.assertEqual(sender.email, 'sender@example.com')
    
    def test_unique_together(self):
        """Teste de constraint unique_together."""
        Sender.objects.create(
            user=self.user,
            email='sender@example.com'
        )
        
        # Tentar criar novamente deve falhar
        with self.assertRaises(Exception):
            Sender.objects.create(
                user=self.user,
                email='sender@example.com'
            )
