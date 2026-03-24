from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
import json
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.auth_app.models import WhatsAppSender, WhatsAppTemplate
from api.services.whatsapp_service import WhatsAppService


class ApiTests(TestCase):
    def test_health(self):
        resp = self.client.get(reverse('health'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'status': 'ok'})

    def test_send_email_success(self):
        payload = {
            'channel': 'email',
            'subject': 'Test Subject',
            'message': 'Hello {Nome}',
            'headers': ['Nome', 'Email'],
            'rows': [
                {'Nome': 'João', 'Email': 'joao@example.com'},
                {'Nome': 'Maria', 'Email': 'maria@example.com'}
            ],
            'contact_column': 'Email',
            'file_column': None,
            'attach_to_all': False
        }
        resp = self.client.post(reverse('send'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data['status'], 'queued')
        self.assertEqual(data['channel'], 'email')
        self.assertEqual(data['total'], 2)
        self.assertIn('previews', data)
        self.assertEqual(len(data['previews']), 2)
        self.assertEqual(data['previews'][0]['destinatario'], 'joao@example.com')
        self.assertEqual(data['previews'][0]['assunto'], 'Test Subject')
        self.assertIn('João', data['previews'][0]['mensagem'])

    def test_send_email_missing(self):
        payload = {'channel': 'email', 'rows': [], 'contact_column': '', 'subject': 'test', 'message': 'test'}
        resp = self.client.post(reverse('send'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_send_whatsapp_success(self):
        payload = {
            'channel': 'whatsapp',
            'message': 'Olá {Nome}',
            'headers': ['Nome', 'Telefone'],
            'rows': [
                {'Nome': 'João', 'Telefone': '+5511999999999'},
                {'Nome': 'Maria', 'Telefone': '+5511988888888'}
            ],
            'contact_column': 'Telefone',
            'file_column': None,
            'attach_to_all': False
        }
        resp = self.client.post(reverse('send'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data['status'], 'queued')
        self.assertEqual(data['channel'], 'whatsapp')
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['previews'][0]['destinatario'], '+5511999999999')
        self.assertIn('João', data['previews'][0]['mensagem'])

    def test_send_invalid_channel(self):
        payload = {'channel': 'sms', 'rows': [], 'contact_column': ''}
        resp = self.client.post(reverse('send'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Invalid channel', resp.json()['error'])

    def test_send_with_attachments_json(self):
        # Test with attachment_names provided in JSON (simulating what frontend would do after collecting files)
        payload = {
            'channel': 'email',
            'subject': 'With Attachments',
            'message': 'File: {arquivo}',
            'headers': ['Nome', 'Email', 'arquivo'],
            'rows': [
                {'Nome': 'A', 'Email': 'a@example.com', 'arquivo': 'foo.pdf'},
                {'Nome': 'B', 'Email': 'b@example.com', 'arquivo': 'bar.pdf'}
            ],
            'contact_column': 'Email',
            'file_column': 'arquivo',
            'attach_to_all': False,
            'attachment_names': ['foo.pdf', 'bar.pdf']  # Simulating files collected
        }
        resp = self.client.post(
            reverse('send'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 202)
        response_data = resp.json()
        self.assertEqual(response_data['status'], 'queued')
        self.assertEqual(len(response_data['previews']), 2)
        # First recipient should get foo.pdf, second should get bar.pdf
        self.assertIn('foo.pdf', response_data['previews'][0]['anexos'])
        self.assertIn('bar.pdf', response_data['previews'][1]['anexos'])


class WhatsAppTemplatePayloadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='whatsapp-user',
            email='whatsapp@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

        self.sender = WhatsAppSender.objects.create(
            user=self.user,
            phone_number='5541999999999',
            phone_number_id='123456789',
            waba_id='987654321',
        )
        self.sender.set_access_token('secret-token')
        self.sender.save()

        self.template = WhatsAppTemplate.objects.create(
            sender=self.sender,
            title='pagamento_boletos_mensalidade',
        )

    @patch('api.services.whatsapp_service.WhatsAppService.send')
    def test_send_whatsapp_template_defaults_to_named_and_maps_name_field(self, send_mock):
        send_mock.return_value = {
            'status': 'success',
            'previews': [],
            'summary': {'total': 1, 'success': 1, 'failed': 0},
        }

        payload = {
            'channel': 'whatsapp',
            'whatsapp_sender_id': str(self.sender.id),
            'whatsapp_template_title': self.template.title,
            'whatsapp_template_language_code': 'pt_BR',
            'rows': [
                {'Nome': 'Gustavo', 'Celular': '5541997393566'}
            ],
            'contact_column': 'Celular',
            'whatsapp_template_variables': [
                {'name': 'aluno', 'mode': 'column', 'column': 'Nome'},
                {'name': 'data', 'mode': 'fixed', 'value': '24/03'},
                {'name': 'dia_semana', 'mode': 'fixed', 'value': 'Segunda'},
            ],
        }

        response = self.client.post(reverse('send_whatsapp'), payload, format='json')

        self.assertEqual(response.status_code, 202)
        send_mock.assert_called_once()

        service_payload = send_mock.call_args.args[0]
        resolved_message = service_payload['resolved_template_messages'][0]
        template_payload = resolved_message['template']

        self.assertEqual(template_payload['parameter_format'], 'NAMED')
        self.assertEqual(
            template_payload['components'][0]['parameters'],
            [
                {'type': 'text', 'parameter_name': 'aluno', 'text': 'Gustavo'},
                {'type': 'text', 'parameter_name': 'data', 'text': '24/03'},
                {'type': 'text', 'parameter_name': 'dia_semana', 'text': 'Segunda'},
            ],
        )

    @patch('api.services.whatsapp_service.WhatsAppService.send')
    def test_send_whatsapp_template_positional_ignores_provided_names(self, send_mock):
        send_mock.return_value = {
            'status': 'success',
            'previews': [],
            'summary': {'total': 1, 'success': 1, 'failed': 0},
        }

        payload = {
            'channel': 'whatsapp',
            'whatsapp_sender_id': str(self.sender.id),
            'whatsapp_template_title': self.template.title,
            'whatsapp_template_language_code': 'pt_BR',
            'whatsapp_template_parameter_format': 'POSITIONAL',
            'rows': [
                {'Nome': 'Gustavo', 'Celular': '5541997393566'}
            ],
            'contact_column': 'Celular',
            'whatsapp_template_variables': [
                {'name': 'aluno', 'mode': 'column', 'column': 'Nome'},
                {'name': 'data', 'mode': 'fixed', 'value': '24/03'},
            ],
        }

        response = self.client.post(reverse('send_whatsapp'), payload, format='json')

        self.assertEqual(response.status_code, 202)
        send_mock.assert_called_once()

        service_payload = send_mock.call_args.args[0]
        template_payload = service_payload['resolved_template_messages'][0]['template']

        self.assertNotIn('parameter_format', template_payload)
        self.assertEqual(
            template_payload['components'][0]['parameters'],
            [
                {'type': 'text', 'text': 'Gustavo'},
                {'type': 'text', 'text': '24/03'},
            ],
        )


class WhatsAppServiceTemplateResultTests(TestCase):
    @patch('api.services.whatsapp_service.WhatsAppService._send_template_message')
    def test_returns_error_when_all_template_sends_fail(self, send_template_mock):
        send_template_mock.side_effect = [
            {'success': False, 'status_code': 400, 'error': 'Invalid parameter'},
            {'success': False, 'status_code': 400, 'error': 'Invalid parameter'},
        ]

        payload = {
            'whatsapp_access_token': 'token',
            'whatsapp_phone_number_id': 'phone-id',
            'resolved_template_messages': [
                {'recipient': '5541997393566', 'template': {'name': 'pagamento'}},
                {'recipient': '5541997393567', 'template': {'name': 'pagamento'}},
            ],
        }

        result = WhatsAppService.send(payload)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['summary'], {'total': 2, 'success': 0, 'failed': 2})
        self.assertEqual(result['error'], 'Invalid parameter')

    @patch('api.services.whatsapp_service.WhatsAppService._send_template_message')
    def test_returns_partial_success_when_at_least_one_send_succeeds(self, send_template_mock):
        send_template_mock.side_effect = [
            {'success': True, 'status_code': 200, 'message_id': 'wamid.1'},
            {'success': False, 'status_code': 400, 'error': 'Invalid parameter'},
        ]

        payload = {
            'whatsapp_access_token': 'token',
            'whatsapp_phone_number_id': 'phone-id',
            'resolved_template_messages': [
                {'recipient': '5541997393566', 'template': {'name': 'pagamento'}},
                {'recipient': '5541997393567', 'template': {'name': 'pagamento'}},
            ],
        }

        result = WhatsAppService.send(payload)

        self.assertEqual(result['status'], 'partial_success')
        self.assertEqual(result['summary'], {'total': 2, 'success': 1, 'failed': 1})
