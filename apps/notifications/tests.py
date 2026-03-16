"""Testes da app de Notificações."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from .services import WebhookHandlerService
from .models import WhatsAppWebhookMessage


class WebhookTests(TestCase):
    """Testes de webhooks."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='frontend_user',
            email='frontend@example.com',
            password='senha-teste-123',
        )
        self.client.force_authenticate(user=self.user)

        self.payload_1 = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': '950713500895823',
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '554163470704',
                            'phone_number_id': '1012541245279634',
                        },
                        'contacts': [{
                            'profile': {'name': 'Gustavo Faria Cardoso'},
                            'wa_id': '554197393566',
                        }],
                        'messages': [{
                            'from': '554197393566',
                            'id': 'wamid.HBgMNTU0MTk3MzkzNTY2FQIAEhgWM0VCMEEwRjg2N0ZBODYwOEJEMjExMgA=',
                            'timestamp': '1773680263',
                            'text': {'body': 'Ola'},
                            'type': 'text',
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }
        self.payload_2 = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': '950713500895823',
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '554163470704',
                            'phone_number_id': '1012541245279634',
                        },
                        'contacts': [{
                            'profile': {'name': 'Gustavo Faria Cardoso'},
                            'wa_id': '554197393566',
                        }],
                        'messages': [{
                            'from': '554197393566',
                            'id': 'wamid.HBgMNTU0MTk3MzkzNTY2FQIAEhgWM0VCMDJFMzBERkNENEE5REI5NzA2QQA=',
                            'timestamp': '1773680267',
                            'text': {'body': 'oi'},
                            'type': 'text',
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }

        self.message_ids = [
            self.payload_1['entry'][0]['changes'][0]['value']['messages'][0]['id'],
            self.payload_2['entry'][0]['changes'][0]['value']['messages'][0]['id'],
        ]

        WhatsAppWebhookMessage.objects.filter(whatsapp_message_id__in=self.message_ids).delete()
        WebhookHandlerService.log_webhook_event(self.payload_1)
        WebhookHandlerService.log_webhook_event(self.payload_2)

    def test_whatsapp_inbox_returns_frontend_payload(self):
        """Retorna lista de conversas e timeline para o frontend."""
        url = reverse('notifications:whatsapp-inbox')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()['ui_components']

        self.assertIn('conversation_list', payload)
        self.assertIn('message_timeline', payload)
        self.assertEqual(payload['stats']['conversations'], 1)
        self.assertEqual(payload['stats']['loaded_messages'], 2)
        self.assertEqual(payload['conversation_list'][0]['contact_name'], 'Gustavo Faria Cardoso')
        self.assertEqual(payload['conversation_list'][0]['last_message'], 'oi')

        timeline = payload['message_timeline'][0]['messages']
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]['text'], 'Ola')
        self.assertEqual(timeline[1]['text'], 'oi')

    def test_whatsapp_inbox_supports_wa_id_filter(self):
        """Permite carregar uma conversa especifica por wa_id."""
        url = reverse('notifications:whatsapp-inbox')
        response = self.client.get(url, {'wa_id': '554197393566'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()['ui_components']
        self.assertEqual(payload['stats']['wa_id_filter'], '554197393566')
        self.assertEqual(len(payload['conversation_list']), 1)
        self.assertEqual(payload['conversation_list'][0]['wa_id'], '554197393566')
