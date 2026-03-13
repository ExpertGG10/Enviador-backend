"""Views de Notificações e Webhooks."""

import json
import os
import unicodedata
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from .services import WhatsAppAPIService, WebhookHandlerService

import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_callback_view(request):
    """Endpoint básico para verificação e recebimento de webhooks do WhatsApp Cloud API."""
    if request.method == 'GET':
        hub_mode = request.GET.get('hub.mode')
        hub_challenge = request.GET.get('hub.challenge')
        hub_verify_token = request.GET.get('hub.verify_token')

        verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN') or os.getenv('MYTOKEN', 'test_token_123')

        if hub_mode == 'subscribe' and hub_verify_token == verify_token and hub_challenge is not None:
            logger.info('Webhook WhatsApp verificado com sucesso')
            return HttpResponse(hub_challenge, content_type='text/plain', status=200)

        logger.warning('Falha na verificação do webhook WhatsApp')
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        data = request.data if isinstance(request.data, dict) else {}
    except Exception:
        data = {}

    if not data:
        try:
            data = json.loads(request.body.decode('utf-8') if request.body else '{}')
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    logger.info('Webhook WhatsApp recebido')
    logger.info(json.dumps(data, ensure_ascii=False, indent=2))

    try:
        if (
            data.get('entry')
            and data['entry'][0].get('changes')
            and data['entry'][0]['changes'][0].get('value')
            and data['entry'][0]['changes'][0]['value'].get('messages')
            and data['entry'][0]['changes'][0]['value']['messages'][0]
        ):
            value = data['entry'][0]['changes'][0]['value']
            message = value['messages'][0]
            phone_number_id = value.get('metadata', {}).get('phone_number_id')
            sender = message.get('from')
            msg_body = (message.get('text') or {}).get('body', '')

            logger.info(f'phone_number_id={phone_number_id}')
            logger.info(f'from={sender}')
            logger.info(f'message={msg_body}')

            _send_whatsapp_reply(phone_number_id, sender, msg_body)
    except Exception:
        logger.exception('Erro ao extrair campos básicos do webhook WhatsApp')

    return JsonResponse({'status': 'received'}, status=200)


def _normalize(text: str) -> str:
    """Remove acentos e converte para minúsculas para comparação."""
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii').lower()


def _send_whatsapp_reply(phone_number_id: str, to: str, received_body: str):
    """Envia resposta automática via WhatsApp Cloud API."""
    access_token = os.getenv('TOKEN')
    if not access_token or not phone_number_id or not to:
        logger.warning('Resposta automática ignorada: TOKEN, phone_number_id ou destinatário ausente')
        return

    reply_text = 'ola' if 'ola' in _normalize(received_body) else 'Nem me deu ola'

    url = f'https://graph.facebook.com/v22.0/{phone_number_id}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to,
        'type': 'text',
        'text': {'preview_url': False, 'body': reply_text},
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(f'Resposta enviada para {to}: "{reply_text}" | status={resp.status_code}')
        if not resp.ok:
            logger.warning(f'Erro na resposta automática: {resp.text}')
    except requests.RequestException:
        logger.exception('Falha ao enviar resposta automática WhatsApp')


class WhatsAppTestView(APIView):
    """Endpoint para testar conexão com API do WhatsApp."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/notifications/whatsapp/test/
        
        Body:
        {
            "phone_number": "5541997393566",
            "template_name": "template_name",
            "language_code": "pt_BR"
        }
        """
        phone_number = request.data.get('phone_number', '5541997393566')
        template_name = request.data.get('template_name', 'hello_world')
        language_code = request.data.get('language_code', 'pt_BR')
        
        logger.info(f"Testando WhatsApp para {phone_number}")
        
        service = WhatsAppAPIService()
        result = service.send_template_message(
            to_number=phone_number,
            template_name=template_name,
            language_code=language_code
        )
        
        status_code = HTTP_200_OK if result.get('success') else HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)


@require_http_methods(["POST"])
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_view(request):
    """
    Webhook endpoint para receber eventos do WhatsApp/Meta.
    
    POST /api/notifications/whatsapp/webhook/
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    logger.info(f"Webhook recebido de {request.META.get('HTTP_ORIGIN', 'UNKNOWN')}")
    
    # Log do evento
    WebhookHandlerService.log_webhook_event(data)
    
    # Parse do evento
    events = WebhookHandlerService.parse_webhook_event(data)
    
    if events:
        logger.info(f"{len(events)} evento(s) processado(s)")
        for event in events:
            logger.debug(f"Evento: {event.get('type')}")
    
    # Sempre retornar 200 para confirmar recebimento
    return JsonResponse({'status': 'received'}, status=200)


@require_http_methods(["GET"])
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def whatsapp_webhook_verify_view(request):
    """
    Webhook verification endpoint.
    Meta chama isso para verificar a URL do webhook.
    
    GET /api/notifications/whatsapp/webhook/verify?hub.mode=subscribe&hub.challenge=xxx&hub.verify_token=xxx
    """
    import os
    
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'test_token_123')
    
    hub_mode = request.GET.get('hub.mode')
    hub_challenge = request.GET.get('hub.challenge')
    hub_verify_token = request.GET.get('hub.verify_token')
    
    if hub_mode == 'subscribe' and hub_verify_token == verify_token:
        logger.info("Webhook verificado com sucesso")
        return JsonResponse(int(hub_challenge), safe=False)
    
    logger.warning("Falha na verificação do webhook")
    return JsonResponse({'error': 'Forbidden'}, status=403)
