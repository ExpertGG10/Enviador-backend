from django.test import TestCase
from django.urls import reverse
import json
from django.core.files.uploadedfile import SimpleUploadedFile


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
