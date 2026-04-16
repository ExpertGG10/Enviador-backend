"""Testes da app de Autenticação."""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
from rest_framework.authtoken.models import Token

from .models import GmailSender, WhatsAppSender, WhatsAppTemplate
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
            waba_id='654321',
        )
        self.sender.set_access_token('secret-token')
        self.sender.save()

        self.template = WhatsAppTemplate.objects.create(
            sender=self.sender,
            title='envio_de_notas_fiscais',
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

    def test_settings_put_updates_gmail_app_password(self):
        gmail_sender = GmailSender.objects.create(
            user=self.user,
            sender_email='financeiro@example.com',
        )
        gmail_sender.set_app_password('old-password')
        gmail_sender.save()

        payload = {
            'gmailSenders': [
                {
                    'id': str(gmail_sender.id),
                    'senderEmail': 'financeiro@example.com',
                    'appPassword': 'new-app-password-123'
                }
            ]
        }

        response = self.client.put('/api/account/settings/', payload, format='json')
        self.assertEqual(response.status_code, HTTP_200_OK)

        gmail_sender.refresh_from_db()
        self.assertEqual(gmail_sender.get_app_password(), 'new-app-password-123')

    def test_settings_put_updates_gmail_app_password_with_snake_case(self):
        gmail_sender = GmailSender.objects.create(
            user=self.user,
            sender_email='contato@example.com',
        )
        gmail_sender.set_app_password('old-password')
        gmail_sender.save()

        payload = {
            'gmail_senders': [
                {
                    'id': str(gmail_sender.id),
                    'sender_email': 'contato@example.com',
                    'app_password': 'new-app-password-xyz'
                }
            ]
        }

        response = self.client.put('/api/account/settings/', payload, format='json')
        self.assertEqual(response.status_code, HTTP_200_OK)

        gmail_sender.refresh_from_db()
        self.assertEqual(gmail_sender.get_app_password(), 'new-app-password-xyz')

    def test_settings_put_requires_known_sender_keys(self):
        response = self.client.put(
            '/api/account/settings/',
            {'invalidField': []},
            format='json'
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class AccountSettingsIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/account/settings/'

        self.user_a = User.objects.create_user(
            username='user-a',
            email='a@example.com',
            password='testpass123'
        )
        self.user_b = User.objects.create_user(
            username='user-b',
            email='b@example.com',
            password='testpass123'
        )

        self.token_a = Token.objects.create(user=self.user_a)
        self.token_b = Token.objects.create(user=self.user_b)

        self.gmail_a = GmailSender.objects.create(
            user=self.user_a,
            sender_email='a@gmail.com',
        )
        self.gmail_a.set_app_password('secret-a')
        self.gmail_a.save()

        self.gmail_b = GmailSender.objects.create(
            user=self.user_b,
            sender_email='b@gmail.com',
        )
        self.gmail_b.set_app_password('secret-b')
        self.gmail_b.save()

        self.whatsapp_a = WhatsAppSender.objects.create(
            user=self.user_a,
            phone_number='5511990000001',
            phone_number_id='pnid-a',
            waba_id='waba-a',
        )
        self.whatsapp_a.set_access_token('token-a')
        self.whatsapp_a.save()
        WhatsAppTemplate.objects.create(sender=self.whatsapp_a, title='tpl_a')

        self.whatsapp_b = WhatsAppSender.objects.create(
            user=self.user_b,
            phone_number='5511990000002',
            phone_number_id='pnid-b',
            waba_id='waba-b',
        )
        self.whatsapp_b.set_access_token('token-b')
        self.whatsapp_b.save()
        WhatsAppTemplate.objects.create(sender=self.whatsapp_b, title='tpl_b')

    def test_account_settings_returns_only_authenticated_user_data(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        response = self.client.get(self.url, format='json')

        self.assertEqual(response.status_code, HTTP_200_OK)

        gmail_senders = response.data.get('gmailSenders', [])
        whatsapp_senders = response.data.get('whatsappSenders', [])

        self.assertEqual(len(gmail_senders), 1)
        self.assertEqual(gmail_senders[0]['senderEmail'], 'a@gmail.com')

        self.assertEqual(len(whatsapp_senders), 1)
        self.assertEqual(whatsapp_senders[0]['phoneNumber'], '5511990000001')
        self.assertEqual(len(whatsapp_senders[0].get('templates', [])), 1)
        self.assertEqual(whatsapp_senders[0]['templates'][0]['name'], 'tpl_a')

    def test_account_settings_rejects_bearer_token_header(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a.key}')
        response = self.client.get(self.url, format='json')

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
