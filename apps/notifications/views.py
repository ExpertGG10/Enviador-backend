"""Views de Notificações e Webhooks."""

import json
from django.http import JsonResponse
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
