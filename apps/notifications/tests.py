"""Testes da app de Notificações."""

import tempfile
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APIClient

from .services import WebhookHandlerService
from .models import WhatsAppWebhookMessage, WhatsAppOutboundMessage, WhatsAppMediaAsset
from apps.auth_app.models import WhatsAppSender


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='notifications-test-media-')


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

        self.sender = WhatsAppSender.objects.create(
            user=self.user,
            phone_number='15550783881',
            phone_number_id='106540352242922',
            waba_id='102290129340398',
        )
        self.sender.set_access_token('test-access-token')
        self.sender.save()

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

    def test_webhook_status_updates_outbound_message_to_recebido_and_lido(self):
        message_id = 'wamid.HBgLMTY1MDM4Nzk0MzkVAgARGBI3MTE5MjVBOTE3MDk5QUVFM0YA'
        outbound = WhatsAppOutboundMessage.objects.create(
            to_wa_id='16505551234',
            text_body='Mensagem teste',
            whatsapp_message_id=message_id,
            phone_number_id='106540352242922',
            status='enviado',
            sent_by=self.user,
            payload={},
        )

        delivered_payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': '102290129340398',
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '15550783881',
                            'phone_number_id': '106540352242922',
                        },
                        'statuses': [{
                            'id': message_id,
                            'status': 'delivered',
                            'timestamp': '1750263773',
                            'recipient_id': '16505551234',
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }

        read_payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': '102290129340398',
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '15550783881',
                            'phone_number_id': '106540352242922',
                        },
                        'statuses': [{
                            'id': message_id,
                            'status': 'read',
                            'timestamp': '1750263799',
                            'recipient_id': '16505551234',
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }

        WebhookHandlerService.log_webhook_event(delivered_payload)
        outbound.refresh_from_db()
        self.assertEqual(outbound.status, 'recebido')
        self.assertEqual(outbound.payload['last_webhook_status']['raw_status'], 'delivered')

        WebhookHandlerService.log_webhook_event(read_payload)
        outbound.refresh_from_db()
        self.assertEqual(outbound.status, 'lido')
        self.assertEqual(outbound.payload['last_webhook_status']['raw_status'], 'read')
        self.assertEqual(len(outbound.payload.get('status_history', [])), 2)

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    @patch('apps.notifications.services.requests.get')
    def test_image_webhook_creates_media_asset_and_stores_file(self, requests_get_mock):
        media_meta_response = Mock()
        media_meta_response.ok = True
        media_meta_response.json.return_value = {
            'url': 'https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=abc123',
        }

        media_binary_response = Mock()
        media_binary_response.ok = True
        media_binary_response.content = b'fake-image-bytes'

        requests_get_mock.side_effect = [media_meta_response, media_binary_response]

        payload = {
            'object': 'whatsapp_business_account',
            'entry': [{
                'id': '102290129340398',
                'changes': [{
                    'value': {
                        'messaging_product': 'whatsapp',
                        'metadata': {
                            'display_phone_number': '15550783881',
                            'phone_number_id': '106540352242922',
                        },
                        'contacts': [{
                            'profile': {'name': 'Sheena Nelson'},
                            'wa_id': '16505551234',
                        }],
                        'messages': [{
                            'from': '16505551234',
                            'id': 'wamid.HBgLMTY1MDM4Nzk0MzkVAgASGBQzQTRBNjU5OUFFRTAzODEwMTQ0RgA=',
                            'timestamp': '1744344496',
                            'type': 'image',
                            'image': {
                                'caption': 'Taj Mahal',
                                'mime_type': 'image/jpeg',
                                'sha256': 'SfInY0gGKTsJlUWbwxC1k+FAD0FZHvzwfpvO0zX0GUI=',
                                'id': '1003383421387256',
                            },
                        }],
                    },
                    'field': 'messages',
                }],
            }],
        }

        WebhookHandlerService.log_webhook_event(payload)

        message = WhatsAppWebhookMessage.objects.get(whatsapp_message_id=payload['entry'][0]['changes'][0]['value']['messages'][0]['id'])
        asset = WhatsAppMediaAsset.objects.get(webhook_message=message)

        self.assertEqual(asset.status, 'ready')
        self.assertEqual(asset.media_type, 'image')
        self.assertEqual(asset.mime_type, 'image/jpeg')
        self.assertEqual(asset.media_id, '1003383421387256')
        self.assertTrue(bool(asset.file.name))
        self.assertEqual(asset.file_size_bytes, len(b'fake-image-bytes'))

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_media_access_endpoint_returns_file_url_for_ready_asset(self):
        message = WhatsAppWebhookMessage.objects.filter(from_wa_id='554197393566').order_by('-id').first()
        self.assertIsNotNone(message)

        asset = WhatsAppMediaAsset.objects.create(
            webhook_message=message,
            whatsapp_message_id=message.whatsapp_message_id,
            media_id='media.local',
            media_type='image',
            mime_type='image/jpeg',
            status='ready',
        )
        asset.file.save('test.jpg', ContentFile(b'abc'), save=True)

        url = reverse('notifications:whatsapp-media-access', kwargs={'asset_id': asset.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['asset_id'], asset.id)
        self.assertEqual(data['status'], 'ready')
        self.assertIn('url', data)
