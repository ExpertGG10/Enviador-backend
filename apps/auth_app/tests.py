"""Testes da app de Autenticação."""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST

from .models import WhatsAppSender, WhatsAppTemplate
from .serializers import WhatsAppTemplateSerializer


class AuthenticationTests(TestCase):
    """Testes de autenticação."""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
    
    def test_register(self):
        """Teste de registro de usuário."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password2': 'testpass123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIn('token', response.data)
    
    def test_login(self):
        """Teste de login."""
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn('token', response.data)


class WhatsAppTemplateSerializerTests(TestCase):
    def test_accepts_name_and_serializes_name(self):
        serializer = WhatsAppTemplateSerializer(data={'name': 'envio_de_notas_fiscais'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['title'], 'envio_de_notas_fiscais')


class AccountSettingsTemplateSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='settings-user',
            email='settings@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.sender = WhatsAppSender.objects.create(
            user=self.user,
            phone_number='5541999999999',
            phone_number_id='123456',
            business_id='654321',
        )
        self.sender.set_access_token('secret-token')
        self.sender.save()

        self.template = WhatsAppTemplate.objects.create(
            sender=self.sender,
            title='envio_de_notas_fiscais',
            content='',
        )

    def test_settings_put_upserts_template_by_name_without_id(self):
        payload = {
            'whatsappSenders': [
                {
                    'id': str(self.sender.id),
                    'templates': [
                        {'name': 'envio_de_notas_fiscais'}
                    ]
                }
            ]
        }

        response = self.client.put('/api/account/settings/', payload, format='json')
        self.assertEqual(response.status_code, HTTP_200_OK)

        templates = WhatsAppTemplate.objects.filter(sender=self.sender)
        self.assertEqual(templates.count(), 1)
        self.assertEqual(templates.first().title, 'envio_de_notas_fiscais')

    def test_settings_put_ignores_complex_whatsapp_template_fields_and_keeps_only_name(self):
        payload = {
            'whatsappSenders': [
                {
                    'id': str(self.sender.id),
                    'templates': [
                        {
                            'name': 'boleto_vencendo',
                            'language': 'pt_BR',
                            'category': 'UTILITY',
                            'components': [
                                {
                                    'type': 'BODY',
                                    'text': 'Seu boleto vence amanhã.'
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        response = self.client.put('/api/account/settings/', payload, format='json')
        self.assertEqual(response.status_code, HTTP_200_OK)

        templates = list(WhatsAppTemplate.objects.filter(sender=self.sender).order_by('title'))
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].title, 'boleto_vencendo')
        self.assertEqual(templates[0].content, '')
