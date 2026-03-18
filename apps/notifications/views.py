"""Views de Notificações e Webhooks."""

import json
import os
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from .models import WhatsAppWebhookMessage, WhatsAppWebhookContact, WhatsAppOutboundMessage
from .services import WhatsAppAPIService, WebhookHandlerService

import logging

logger = logging.getLogger(__name__)


def _parse_positive_int(value, default: int, maximum: int) -> int:
    """Converte query param para inteiro positivo com limite maximo."""
    try:
        parsed = int(value)
        if parsed < 1:
            return default
        return min(parsed, maximum)
    except (TypeError, ValueError):
        return default


def _build_contact_name_map(wa_ids):
    """Retorna o nome mais recente conhecido por wa_id."""
    names_by_wa_id = {}
    if not wa_ids:
        return names_by_wa_id

    contacts = (
        WhatsAppWebhookContact.objects
        .filter(wa_id__in=wa_ids)
        .order_by('-id')
    )

    for contact in contacts:
        if contact.wa_id not in names_by_wa_id and contact.profile_name:
            names_by_wa_id[contact.wa_id] = contact.profile_name

    return names_by_wa_id


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
        WebhookHandlerService.log_webhook_event(data)
    except Exception:
        logger.exception('Erro ao persistir evento do webhook WhatsApp')

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

    reply_text = 'teste correto'

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
    if 'teste' in _normalize(received_body):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            logger.info(f'Resposta enviada para {to}: "{reply_text}" | status={resp.status_code}')
            
            # Salvar apenas se a mensagem foi enviada com sucesso
            if resp.ok:
                try:
                    response_payload = resp.json()
                except ValueError:
                    response_payload = {'raw_text': resp.text}

                whatsapp_message_id = (
                    response_payload.get('messages', [{}])[0].get('id', '')
                    if isinstance(response_payload, dict)
                    else ''
                )

                WhatsAppOutboundMessage.objects.create(
                    to_wa_id=to,
                    text_body=reply_text,
                    whatsapp_message_id=whatsapp_message_id,
                    phone_number_id=phone_number_id,
                    status='sent',
                    sent_by=None,
                    payload=response_payload if isinstance(response_payload, dict) else {'response': response_payload},
                )
            else:
                # Erro na resposta - não salva, apenas registra no log
                try:
                    error_response = resp.json()
                except ValueError:
                    error_response = {'raw_text': resp.text}
                logger.warning(f'Erro na resposta automática: {error_response}')
        except requests.RequestException as exc:
            # Erro de conexão - não salva, apenas registra no log
            logger.exception(f'Falha ao enviar resposta automática WhatsApp para {to}: {str(exc)}')


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


@require_http_methods(["GET"])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whatsapp_inbox_view(request):
    """Endpoint de inbox para frontend com lista de conversas e timeline."""
    wa_id_filter = request.GET.get('wa_id')
    conversation_limit = _parse_positive_int(request.GET.get('conversation_limit'), default=20, maximum=100)
    message_limit = _parse_positive_int(request.GET.get('message_limit'), default=50, maximum=200)

    inbound_queryset = (
        WhatsAppWebhookMessage.objects
        .select_related('change__entry__event')
        .order_by('-timestamp', '-created_at')
    )
    if wa_id_filter:
        inbound_queryset = inbound_queryset.filter(from_wa_id=wa_id_filter)

    outbound_queryset = WhatsAppOutboundMessage.objects.order_by('-created_at')
    if wa_id_filter:
        outbound_queryset = outbound_queryset.filter(to_wa_id=wa_id_filter)

    inbound_rows = list(inbound_queryset[: conversation_limit * message_limit])
    outbound_rows = list(outbound_queryset[: conversation_limit * message_limit])

    unified_rows = []
    for msg in inbound_rows:
        unified_rows.append({
            'wa_id': msg.from_wa_id,
            'message_id': msg.whatsapp_message_id,
            'type': msg.message_type,
            'text': msg.text_body,
            'timestamp': msg.timestamp,
            'datetime_iso': datetime.fromtimestamp(msg.timestamp, tz=timezone.utc).isoformat() if msg.timestamp else None,
            'direction': 'inbound',
            'phone_number_id': msg.change.phone_number_id,
            'display_phone_number': msg.change.display_phone_number,
            'event_id': msg.change.entry.event_id,
            'sort_key': msg.timestamp or int(msg.created_at.timestamp()),
        })

    for msg in outbound_rows:
        outbound_ts = int(msg.created_at.timestamp())
        unified_rows.append({
            'wa_id': msg.to_wa_id,
            'message_id': msg.whatsapp_message_id or f'local-{msg.id}',
            'type': 'text',
            'text': msg.text_body,
            'timestamp': outbound_ts,
            'datetime_iso': msg.created_at.astimezone(timezone.utc).isoformat(),
            'direction': 'outbound',
            'phone_number_id': msg.phone_number_id,
            'display_phone_number': '',
            'event_id': None,
            'status': msg.status,
            'sort_key': outbound_ts,
        })

    raw_rows = sorted(unified_rows, key=lambda r: (r['sort_key'], r['message_id']))[-(conversation_limit * message_limit):]
    rows = list(raw_rows)

    conversations = defaultdict(list)
    for msg in rows:
        wa_id = msg['wa_id']
        conversations[wa_id].append(msg)

    wa_ids = list(conversations.keys())
    contact_name_map = _build_contact_name_map(wa_ids)

    conversation_list = []
    timeline = []
    for wa_id, items in conversations.items():
        sorted_items = sorted(items, key=lambda i: (i['timestamp'] or 0, i['message_id']))[-message_limit:]
        response_items = [{k: v for k, v in item.items() if k != 'sort_key'} for item in sorted_items]
        last_item = sorted_items[-1] if sorted_items else None

        conversation_list.append({
            'wa_id': wa_id,
            'contact_name': contact_name_map.get(wa_id, 'Sem nome'),
            'last_message': last_item['text'] if last_item else '',
            'last_timestamp': last_item['datetime_iso'] if last_item else None,
            'unread_count': len(sorted_items),
        })
        timeline.append({
            'wa_id': wa_id,
            'contact_name': contact_name_map.get(wa_id, 'Sem nome'),
            'messages': response_items,
        })

    conversation_list = sorted(
        conversation_list,
        key=lambda c: c['last_timestamp'] or '',
        reverse=True,
    )[:conversation_limit]

    ordered_wa_ids = [c['wa_id'] for c in conversation_list]
    timeline = sorted(
        timeline,
        key=lambda block: ordered_wa_ids.index(block['wa_id']) if block['wa_id'] in ordered_wa_ids else 10**9,
    )

    payload = {
        'ui_components': {
            'conversation_list': conversation_list,
            'message_timeline': timeline,
            'stats': {
                'loaded_messages': sum(len(t['messages']) for t in timeline),
                'conversations': len(conversation_list),
                'wa_id_filter': wa_id_filter,
                'conversation_limit': conversation_limit,
                'message_limit': message_limit,
            },
        }
    }
    return Response(payload, status=HTTP_200_OK)


@require_http_methods(["POST"])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def whatsapp_send_text_view(request):
    """Envia mensagem de texto para um numero WhatsApp e salva no historico."""
    wa_id = str(request.data.get('wa_id', '')).strip()
    text = str(request.data.get('text', '')).strip()

    if not wa_id:
        return Response({'error': 'wa_id é obrigatório'}, status=HTTP_400_BAD_REQUEST)
    if not text:
        return Response({'error': 'text é obrigatório'}, status=HTTP_400_BAD_REQUEST)

    service = WhatsAppAPIService()
    result = service.send_text_message(to_number=wa_id, message=text)

    if not result.get('success'):
        return Response(result, status=HTTP_400_BAD_REQUEST)

    outbound = WhatsAppOutboundMessage.objects.create(
        to_wa_id=wa_id,
        text_body=text,
        whatsapp_message_id=result.get('message_id', ''),
        phone_number_id=service.phone_number_id,
        status=result.get('status', 'sent'),
        sent_by=request.user,
        payload=result,
    )

    response_payload = {
        'status': 'sent',
        'message': {
            'id': outbound.id,
            'wa_id': outbound.to_wa_id,
            'message_id': outbound.whatsapp_message_id,
            'text': outbound.text_body,
            'direction': 'outbound',
            'datetime_iso': outbound.created_at.astimezone(timezone.utc).isoformat(),
            'phone_number_id': outbound.phone_number_id,
        }
    }
    return Response(response_payload, status=HTTP_200_OK)
