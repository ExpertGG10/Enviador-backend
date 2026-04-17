"""Serviços de Notificações (WhatsApp, Webhooks, etc)."""

import os
import requests
import logging
import json
import re
import unicodedata

from django.db import transaction
from django.utils import timezone

from django.core.files.base import ContentFile

from apps.auth_app.models import WhatsAppSender
from .media_registry import MediaTypeRegistry

from .models import (
    WhatsAppWebhookEvent,
    WhatsAppWebhookEntry,
    WhatsAppWebhookChange,
    WhatsAppWebhookContact,
    WhatsAppWebhookMessage,
    WhatsAppOutboundMessage,
    WhatsAppMediaAsset,
    WhatsAppPendingAttachment,
)

logger = logging.getLogger(__name__)


WHATSAPP_STATUS_MAP = {
    'sent': 'enviado',
    'delivered': 'recebido',
    'read': 'lido',
    'failed': 'falha',
}


class WhatsAppAPIService:
    """Serviço para integração com API do WhatsApp/Meta."""
    
    BASE_URL = 'https://graph.facebook.com/v22.0'
    
    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', '')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
        self.business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
        print("[WHATSAPP API SERVICE INIT] Serviço WhatsApp inicializado")
        logger.info("[WHATSAPP API SERVICE INIT] WhatsApp API Service inicializado")
    
    def send_template_message(self, to_number: str, template_name: str, language_code: str = 'pt_BR', params: list = None):
        """
        Enviar mensagem de template via WhatsApp.
        
        Args:
            to_number: Número de telefone do destinatário (com código do país)
            template_name: Nome do template pré-aprovado
            language_code: Código de idioma
            params: Parâmetros para substituição no template
        
        Returns:
            dict com resultado do envio
        """
        try:
            print(f"[WHATSAPP TEMPLATE] Enviando template '{template_name}' para: {to_number}")
            logger.info(f"[WHATSAPP TEMPLATE] Iniciando envio de template: {template_name}")
            url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code,
                        "policy": "deterministic"
                    },
                    "components": []
                }
            }
            
            if params:
                payload["template"]["components"].append({
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params]
                })
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            print(f"[WHATSAPP TEMPLATE] Status da resposta: {response.status_code}")
            response.raise_for_status()
            
            message_id = response.json().get('messages', [{}])[0].get('id')
            logger.info(f"Mensagem WhatsApp enviada para {to_number} - ID: {message_id}")
            print(f"[WHATSAPP TEMPLATE] ✓ Mensagem enviada com sucesso! ID: {message_id}")
            return {
                'success': True,
                'message_id': message_id,
                'status': 'sent'
            }
        
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
            print(f"[WHATSAPP TEMPLATE] ❌ Erro ao enviar para {to_number}: {str(e)}")
            import traceback
            print(f"[WHATSAPP TEMPLATE] Stack trace: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }
    
    def send_text_message(self, to_number: str, message: str, access_token: str = None, phone_number_id: str = None):
        """Enviar mensagem de texto simples.
        
        Args:
            to_number: Número do destinatário
            message: Conteúdo da mensagem
            access_token: Token de acesso (opcional, usa instance se não fornecido)
            phone_number_id: ID do número de telefone (opcional, usa instance se não fornecido)
        """
        try:
            print(f"[WHATSAPP TEXT] Enviando mensagem de texto para: {to_number}")
            print(f"[WHATSAPP TEXT] Conteúdo: {message}")
            logger.info(f"[WHATSAPP TEXT] Enviando texto para: {to_number}")
            
            # Usar credenciais fornecidas ou do instance
            token = access_token or self.access_token
            phone_id = phone_number_id or self.phone_number_id
            
            # Validar configurações
            if not token:
                error_msg = "Access token não configurado."
                print(f"[WHATSAPP TEXT] ❌ {error_msg}")
                logger.error(error_msg)
                return {'success': False, 'error': error_msg, 'status': 'failed'}
            
            if not phone_id:
                error_msg = "Phone number ID não configurado."
                print(f"[WHATSAPP TEXT] ❌ {error_msg}")
                logger.error(error_msg)
                return {'success': False, 'error': error_msg, 'status': 'failed'}
            
            url = f"{self.BASE_URL}/{phone_id}/messages"
            print(f"[WHATSAPP TEXT] URL: {url}")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message}
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            print(f"[WHATSAPP TEXT] Status da resposta: {response.status_code}")
            response.raise_for_status()
            
            message_id = response.json().get('messages', [{}])[0].get('id')
            logger.info(f"Mensagem de texto enviada para {to_number} - ID: {message_id}")
            print(f"[WHATSAPP TEXT] ✓ Mensagem enviada com sucesso! ID: {message_id}")
            return {
                'success': True,
                'message_id': message_id,
                'status': 'sent'
            }
        
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de texto: {str(e)}")
            print(f"[WHATSAPP TEXT] ❌ Erro ao enviar para {to_number}: {str(e)}")
            import traceback
            print(f"[WHATSAPP TEXT] Stack trace: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def upload_media(self, file_obj, mime_type: str, access_token: str = None, phone_number_id: str = None, filename: str = None):
        """Faz upload de mídia para a Cloud API e retorna media_id."""
        try:
            token = access_token or self.access_token
            phone_id = phone_number_id or self.phone_number_id

            if not token:
                return {'success': False, 'error': 'Access token não configurado.', 'status': 'failed'}
            if not phone_id:
                return {'success': False, 'error': 'Phone number ID não configurado.', 'status': 'failed'}
            if not file_obj:
                return {'success': False, 'error': 'Arquivo não fornecido para upload.', 'status': 'failed'}

            url = f"{self.BASE_URL}/{phone_id}/media"
            safe_filename = str(filename or getattr(file_obj, 'name', 'attachment.bin') or 'attachment.bin')
            safe_mime_type = str(mime_type or 'application/octet-stream')

            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)

            files = {
                'file': (safe_filename, file_obj, safe_mime_type),
            }
            data = {'messaging_product': 'whatsapp'}
            headers = {'Authorization': f'Bearer {token}'}

            response = requests.post(url, data=data, files=files, headers=headers, timeout=60)
            response.raise_for_status()

            payload = response.json() if response.content else {}
            media_id = payload.get('id') if isinstance(payload, dict) else None
            if not media_id:
                return {
                    'success': False,
                    'error': 'Meta API não retornou media_id no upload.',
                    'status': 'failed',
                    'payload': payload,
                }

            return {
                'success': True,
                'status': 'uploaded',
                'media_id': str(media_id),
                'payload': payload,
            }

        except Exception as e:
            logger.error(f"Erro ao fazer upload de mídia WhatsApp: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
            }

    def send_document_message(
        self,
        to_number: str,
        media_id: str,
        caption: str = '',
        filename: str = '',
        access_token: str = None,
        phone_number_id: str = None,
    ):
        """Envia documento já carregado na Meta para um contato WhatsApp."""
        try:
            token = access_token or self.access_token
            phone_id = phone_number_id or self.phone_number_id

            if not token:
                return {'success': False, 'error': 'Access token não configurado.', 'status': 'failed'}
            if not phone_id:
                return {'success': False, 'error': 'Phone number ID não configurado.', 'status': 'failed'}
            if not to_number:
                return {'success': False, 'error': 'Destinatário não informado.', 'status': 'failed'}
            if not media_id:
                return {'success': False, 'error': 'media_id não informado.', 'status': 'failed'}

            url = f"{self.BASE_URL}/{phone_id}/messages"
            document_payload = {'id': str(media_id)}
            if caption:
                document_payload['caption'] = str(caption)
            if filename:
                document_payload['filename'] = str(filename)

            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': str(to_number),
                'type': 'document',
                'document': document_payload,
            }
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            response_payload = response.json() if response.content else {}
            message_id = ''
            if isinstance(response_payload, dict):
                message_id = response_payload.get('messages', [{}])[0].get('id', '')

            return {
                'success': True,
                'status': 'sent',
                'message_id': message_id,
                'payload': response_payload,
            }

        except Exception as e:
            logger.error(f"Erro ao enviar documento WhatsApp: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
            }


class PendingAttachmentDispatchService:
    """Processa eventos de botao e dispara anexos pendentes para o contato."""

    @staticmethod
    def _normalize_wa_id(wa_id: str) -> str:
        return re.sub(r'\D+', '', str(wa_id or ''))

    @staticmethod
    def _wa_id_variants(wa_id: str):
        """Gera variações simples para celular BR com/sem nono dígito."""
        normalized = PendingAttachmentDispatchService._normalize_wa_id(wa_id)
        variants = {normalized} if normalized else set()

        if not normalized.startswith('55'):
            return variants

        local = normalized[2:]
        # 55 + DDD(2) + 9 + numero(8)
        if len(local) == 11 and local[2:3] == '9':
            variants.add('55' + local[:2] + local[3:])
        # 55 + DDD(2) + numero(8)
        if len(local) == 10:
            variants.add('55' + local[:2] + '9' + local[2:])

        return variants

    @staticmethod
    def _normalize_button_payload(payload: str) -> str:
        text = str(payload or '').strip()
        if not text:
            return ''

        ascii_text = (
            unicodedata.normalize('NFD', text)
            .encode('ascii', 'ignore')
            .decode('ascii')
        )
        canonical = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_text).strip('_').upper()
        return canonical

    @staticmethod
    def dispatch_from_webhook_payload(data: dict):
        triggers = PendingAttachmentDispatchService._extract_button_triggers(data)
        for trigger in triggers:
            try:
                PendingAttachmentDispatchService._dispatch_trigger(
                    phone_number_id=trigger['phone_number_id'],
                    wa_id=trigger['wa_id'],
                    button_payload=trigger['button_payload'],
                    trigger_message_id=trigger['trigger_message_id'],
                    raw_message=trigger['raw_message'],
                )
            except Exception:
                logger.exception(
                    '[PENDING ATTACHMENT] Erro ao processar trigger wa_id=%s payload=%s',
                    trigger.get('wa_id'),
                    trigger.get('button_payload'),
                )

    @staticmethod
    def _extract_button_triggers(data: dict):
        triggers = []
        entries = data.get('entry') if isinstance(data, dict) else []
        if not isinstance(entries, list):
            return triggers

        for entry in entries:
            changes = entry.get('changes') if isinstance(entry, dict) else []
            if not isinstance(changes, list):
                continue

            for change in changes:
                value = change.get('value') if isinstance(change, dict) else {}
                if not isinstance(value, dict):
                    continue

                phone_number_id = str((value.get('metadata') or {}).get('phone_number_id') or '').strip()
                messages = value.get('messages') or []
                if not isinstance(messages, list):
                    continue

                for message in messages:
                    if not isinstance(message, dict):
                        continue

                    button_payload = PendingAttachmentDispatchService._extract_button_payload(message)
                    if not button_payload:
                        continue

                    wa_id = str(message.get('from') or '').strip()
                    trigger_message_id = str(message.get('id') or '').strip()
                    if not wa_id or not phone_number_id:
                        continue

                    triggers.append({
                        'phone_number_id': phone_number_id,
                        'wa_id': wa_id,
                        'button_payload': button_payload,
                        'trigger_message_id': trigger_message_id,
                        'raw_message': message,
                    })

        return triggers

    @staticmethod
    def _extract_button_payload(message: dict) -> str:
        message_type = str(message.get('type') or '').strip().lower()

        if message_type == 'interactive':
            interactive = message.get('interactive')
            if isinstance(interactive, dict):
                button_reply = interactive.get('button_reply')
                if isinstance(button_reply, dict):
                    return str(button_reply.get('id') or '').strip()

        if message_type == 'button':
            button_block = message.get('button')
            if isinstance(button_block, dict):
                return str(button_block.get('payload') or '').strip()

        return ''

    @staticmethod
    def _dispatch_trigger(phone_number_id: str, wa_id: str, button_payload: str, trigger_message_id: str, raw_message: dict):
        sender = (
            WhatsAppSender.objects
            .filter(phone_number_id=phone_number_id)
            .order_by('-created_at')
            .first()
        )
        if sender is None:
            logger.warning('[PENDING ATTACHMENT] Sender não encontrado para phone_number_id=%s', phone_number_id)
            return

        normalized_wa_variants = PendingAttachmentDispatchService._wa_id_variants(wa_id)
        normalized_payload = PendingAttachmentDispatchService._normalize_button_payload(button_payload)

        with transaction.atomic():
            pending_queryset = (
                WhatsAppPendingAttachment.objects
                .select_for_update()
                .filter(sender=sender, status='pending')
                .order_by('created_at')
            )

            # Primeiro tenta match exato (mais barato e previsível).
            pending = (
                pending_queryset
                .filter(wa_id=wa_id, button_payload=button_payload)
                .first()
            )

            # Fallback simples para inconsistências comuns de formatação.
            if pending is None:
                for candidate in pending_queryset[:200]:
                    candidate_wa = PendingAttachmentDispatchService._normalize_wa_id(candidate.wa_id)
                    candidate_payload = PendingAttachmentDispatchService._normalize_button_payload(candidate.button_payload)
                    if candidate_wa in normalized_wa_variants and candidate_payload == normalized_payload:
                        pending = candidate
                        logger.info(
                            '[PENDING ATTACHMENT] Match normalizado pending_id=%s webhook_wa_id=%s stored_wa_id=%s webhook_payload=%s stored_payload=%s',
                            pending.id,
                            wa_id,
                            candidate.wa_id,
                            button_payload,
                            candidate.button_payload,
                        )
                        break

            if pending is None:
                logger.info(
                    '[PENDING ATTACHMENT] Sem pendência para sender=%s wa_id=%s payload=%s',
                    sender.id,
                    wa_id,
                    button_payload,
                )
                return

            if trigger_message_id and pending.trigger_message_id == trigger_message_id and pending.status in ('sending', 'sent'):
                logger.info('[PENDING ATTACHMENT] Trigger duplicado ignorado pending_id=%s', pending.id)
                return

            pending.status = 'sending'
            pending.attempts = int(pending.attempts or 0) + 1
            pending.trigger_message_id = trigger_message_id
            pending.error_message = ''
            pending.save(update_fields=['status', 'attempts', 'trigger_message_id', 'error_message', 'updated_at'])

        api_service = WhatsAppAPIService()
        access_token = sender.get_access_token()

        pending_file = pending.file
        if not pending_file:
            pending.status = 'failed'
            pending.error_message = 'Arquivo pendente não encontrado.'
            pending.save(update_fields=['status', 'error_message', 'updated_at'])
            return

        if hasattr(pending_file, 'open'):
            pending_file.open('rb')

        try:
            upload_result = api_service.upload_media(
                file_obj=pending_file,
                mime_type=pending.mime_type,
                access_token=access_token,
                phone_number_id=sender.phone_number_id,
                filename=pending.original_name or os.path.basename(pending.file.name),
            )
            if not upload_result.get('success'):
                pending.status = 'failed'
                pending.error_message = str(upload_result.get('error') or 'Falha ao subir arquivo para Meta')
                pending.save(update_fields=['status', 'error_message', 'updated_at'])
                return

            send_result = api_service.send_document_message(
                to_number=wa_id,
                media_id=upload_result.get('media_id', ''),
                caption=pending.caption,
                filename=pending.original_name,
                access_token=access_token,
                phone_number_id=sender.phone_number_id,
            )
            if not send_result.get('success'):
                pending.status = 'failed'
                pending.error_message = str(send_result.get('error') or 'Falha ao enviar documento')
                pending.save(update_fields=['status', 'error_message', 'updated_at'])
                return

            outbound_payload = {
                'pending_attachment_id': pending.id,
                'button_payload': button_payload,
                'trigger_message_id': trigger_message_id,
                'trigger_message': raw_message,
                'upload_result': upload_result,
                'send_result': send_result,
            }

            outbound = WhatsAppOutboundMessage.objects.create(
                to_wa_id=wa_id,
                text_body=pending.caption or f"[documento] {pending.original_name or pending.file.name}",
                whatsapp_message_id=send_result.get('message_id', ''),
                phone_number_id=sender.phone_number_id,
                status='enviado' if send_result.get('status') == 'sent' else send_result.get('status', 'enviado'),
                sent_by=sender.user,
                payload=outbound_payload,
            )

            pending.status = 'sent'
            pending.error_message = ''
            pending.sent_at = timezone.now()
            pending.payload = {
                **dict(pending.payload or {}),
                'outbound_id': outbound.id,
                'meta_media_id': upload_result.get('media_id', ''),
                'whatsapp_message_id': send_result.get('message_id', ''),
            }
            pending.save(update_fields=['status', 'error_message', 'sent_at', 'payload', 'updated_at'])
        finally:
            if hasattr(pending_file, 'close'):
                pending_file.close()


class WebhookHandlerService:
    """Serviço para processar webhooks."""

    BASE_URL = 'https://graph.facebook.com/v22.0'

    @staticmethod
    def _map_status(raw_status: str) -> str:
        status_key = str(raw_status or '').strip().lower()
        return WHATSAPP_STATUS_MAP.get(status_key, status_key or 'desconhecido')

    @staticmethod
    def _update_outbound_status(status_payload: dict, change: WhatsAppWebhookChange):
        message_id = str(status_payload.get('id') or '').strip()
        if not message_id:
            return

        outbound = (
            WhatsAppOutboundMessage.objects
            .filter(whatsapp_message_id=message_id)
            .order_by('-created_at')
            .first()
        )
        if outbound is None:
            logger.info('[WEBHOOK STATUS] Mensagem outbound não encontrada para id=%s', message_id)
            return

        mapped_status = WebhookHandlerService._map_status(status_payload.get('status'))

        event = {
            'message_id': message_id,
            'raw_status': status_payload.get('status'),
            'status': mapped_status,
            'timestamp': status_payload.get('timestamp'),
            'recipient_id': status_payload.get('recipient_id'),
            'phone_number_id': change.phone_number_id,
            'conversation': status_payload.get('conversation'),
            'pricing': status_payload.get('pricing'),
            'errors': status_payload.get('errors') or [],
        }

        updated_payload = dict(outbound.payload or {})
        history = list(updated_payload.get('status_history') or [])
        history.append(event)
        updated_payload['status_history'] = history
        updated_payload['last_webhook_status'] = event

        outbound.status = mapped_status
        outbound.payload = updated_payload
        outbound.save(update_fields=['status', 'payload'])
        logger.info(
            '[WEBHOOK STATUS] Outbound atualizado message_id=%s status=%s',
            message_id,
            mapped_status,
        )

    @staticmethod
    def _build_media_filename(message_id: str, mime_type: str, media_type: str, filename_hint: str = None) -> str:
        """Constrói nome de arquivo para mídia com suporte a todos os tipos.
        
        Args:
            message_id: ID da mensagem WhatsApp
            mime_type: MIME type da mídia (ex: image/jpeg, audio/ogg)
            media_type: Tipo de mídia (image, video, document, audio)
            filename_hint: Nome de arquivo opcional (usado para document)
        
        Returns:
            Nome de arquivo sanitizado com extensão apropriada
        """
        sanitized_message_id = re.sub(r'[^a-zA-Z0-9._-]', '_', str(message_id or 'media'))
        
        # Se documento vem com filename, usar como base (com sanitização)
        if filename_hint and media_type == 'document':
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', str(filename_hint).strip())
            if safe_filename:
                return safe_filename
        
        # Mapping MIME type → extensão (cobre todos os tipos)
        extension_by_mime = {
            # Imagens
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/png': 'png',
            'image/webp': 'webp',
            'image/gif': 'gif',
            'image/bmp': 'bmp',
            # Vídeo
            'video/mp4': 'mp4',
            'video/quicktime': 'mov',
            'video/x-msvideo': 'avi',
            'video/x-matroska': 'mkv',
            'video/ogg': 'ogv',
            # Áudio
            'audio/mpeg': 'mp3',
            'audio/ogg': 'ogg',
            'audio/mp4': 'm4a',
            'audio/wav': 'wav',
            'audio/webm': 'webm',
            'audio/aac': 'aac',
            # Documento
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'text/plain': 'txt',
        }
        
        # Tentar extensão via MIME, fallback para tipo de mídia, fallback para 'bin'
        mime_lower = str(mime_type or '').lower()
        extension = extension_by_mime.get(mime_lower) or MediaTypeRegistry.get_default_extension(media_type)
        
        return f'{sanitized_message_id}.{extension}'

    @staticmethod
    def _get_sender_access_token(phone_number_id: str) -> str:
        logger.info('[WEBHOOK MEDIA] Procurando sender para phone_number_id=%s', phone_number_id)
        sender = (
            WhatsAppSender.objects
            .filter(phone_number_id=str(phone_number_id or '').strip())
            .order_by('-created_at')
            .first()
        )
        if not sender:
            logger.warning('[WEBHOOK MEDIA] Sender não encontrado para phone_number_id=%s', phone_number_id)
            return ''
        try:
            token = sender.get_access_token()
            logger.info(
                '[WEBHOOK MEDIA] Sender encontrado id=%s token_len=%s',
                sender.id,
                len(token or ''),
            )
            return token
        except Exception:
            logger.exception('[WEBHOOK MEDIA] Falha ao descriptografar access token para phone_number_id=%s', phone_number_id)
            return ''

    @staticmethod
    def _resolve_media_url(media_payload: dict, phone_number_id: str, access_token: str) -> str:
        direct_url = str(media_payload.get('url') or '').strip()
        if direct_url:
            logger.info('[WEBHOOK MEDIA] URL direta encontrada no payload para media_id=%s', media_payload.get('id'))
            return direct_url

        media_id = str(media_payload.get('id') or '').strip()
        if not media_id or not access_token:
            return ''

        request_url = f"{WebhookHandlerService.BASE_URL}/{media_id}"
        params = {'phone_number_id': str(phone_number_id or '').strip()} if phone_number_id else None
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            logger.info('[WEBHOOK MEDIA] Consultando URL da mídia na Meta media_id=%s phone_number_id=%s', media_id, phone_number_id)
            resp = requests.get(request_url, headers=headers, params=params, timeout=15)
            if not resp.ok:
                logger.warning('[WEBHOOK MEDIA] Falha ao obter URL da mídia id=%s status=%s body=%s', media_id, resp.status_code, resp.text)
                return ''
            payload = resp.json()
            resolved_url = str(payload.get('url') or '').strip()
            logger.info('[WEBHOOK MEDIA] URL da mídia resolvida media_id=%s has_url=%s', media_id, bool(resolved_url))
            return resolved_url
        except requests.RequestException:
            logger.exception('[WEBHOOK MEDIA] Erro ao obter URL da mídia id=%s', media_id)
            return ''

    @staticmethod
    def _download_and_store_media_asset(asset: WhatsAppMediaAsset, media_payload: dict, change: WhatsAppWebhookChange):
        logger.info(
            '[WEBHOOK MEDIA] Iniciando processamento do asset id=%s message_id=%s media_id=%s',
            asset.id,
            asset.whatsapp_message_id,
            asset.media_id,
        )
        access_token = WebhookHandlerService._get_sender_access_token(change.phone_number_id)
        if not access_token:
            asset.status = 'failed'
            asset.error_message = 'Access token não encontrado para phone_number_id'
            asset.save(update_fields=['status', 'error_message', 'updated_at'])
            logger.warning('[WEBHOOK MEDIA] Asset id=%s falhou por ausência de access token', asset.id)
            return

        media_url = WebhookHandlerService._resolve_media_url(media_payload, change.phone_number_id, access_token)
        if not media_url:
            asset.status = 'failed'
            asset.error_message = 'Não foi possível resolver a URL da mídia'
            asset.save(update_fields=['status', 'error_message', 'updated_at'])
            logger.warning('[WEBHOOK MEDIA] Asset id=%s falhou por URL não resolvida', asset.id)
            return

        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            logger.info('[WEBHOOK MEDIA] Baixando mídia asset_id=%s media_id=%s', asset.id, asset.media_id)
            resp = requests.get(media_url, headers=headers, timeout=30)
            if not resp.ok:
                asset.status = 'failed'
                asset.error_message = f'Download da mídia falhou com status {resp.status_code}'
                asset.save(update_fields=['status', 'error_message', 'updated_at'])
                logger.warning('[WEBHOOK MEDIA] Download falhou media_id=%s status=%s', asset.media_id, resp.status_code)
                return

            mime_type = str(asset.mime_type or media_payload.get('mime_type') or '').strip()
            filename_hint = media_payload.get('filename') if asset.media_type == 'document' else None
            file_name = WebhookHandlerService._build_media_filename(
                asset.whatsapp_message_id, 
                mime_type, 
                asset.media_type,
                filename_hint
            )
            asset.file.save(file_name, ContentFile(resp.content), save=False)
            asset.file_size_bytes = len(resp.content)
            asset.status = 'ready'
            asset.error_message = ''
            payload_data = dict(asset.payload or {})
            payload_data['download_source_url'] = media_url
            asset.payload = payload_data
            asset.save(update_fields=['file', 'file_size_bytes', 'status', 'error_message', 'payload', 'updated_at'])
            logger.info(
                '[WEBHOOK MEDIA] Asset salvo com sucesso asset_id=%s file=%s size=%s',
                asset.id,
                asset.file.name,
                asset.file_size_bytes,
            )
        except requests.RequestException:
            asset.status = 'failed'
            asset.error_message = 'Erro de rede ao baixar mídia da Meta'
            asset.save(update_fields=['status', 'error_message', 'updated_at'])
            logger.exception('[WEBHOOK MEDIA] Erro de rede ao baixar mídia media_id=%s', asset.media_id)
    
    @staticmethod
    def parse_webhook_event(data):
        """
        Parse webhook event from Meta.
        
        Returns:
            list of parsed events
        """
        print("\n" + "="*80)
        print("[WEBHOOK HANDLER] ========== PROCESSANDO WEBHOOK EVENT ==========")
        print("="*80)
        logger.info("[WEBHOOK HANDLER] Iniciando parse de webhook event")
        events = []
        
        try:
            print(f"[WEBHOOK HANDLER] Dados brutos: {json.dumps(data, indent=2)}")
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [])
            print(f"[WEBHOOK HANDLER] Número de changes: {len(changes)}")
            
            for change_idx, change in enumerate(changes):
                value = change.get('value', {})
                print(f"[WEBHOOK HANDLER] Processando change {change_idx + 1}/{len(changes)}")
                
                # Processar mensagens
                messages = value.get('messages', [])
                print(f"[WEBHOOK HANDLER] Mensagens encontradas: {len(messages)}")
                for msg_idx, message in enumerate(messages):
                    msg_id = message.get('id')
                    msg_from = message.get('from')
                    msg_text = message.get('text', {}).get('body', '')
                    print(f"[WEBHOOK HANDLER]   - Mensagem {msg_idx + 1}: ID={msg_id}, De={msg_from}, Texto={msg_text[:50]}...")
                    events.append({
                        'type': 'message',
                        'from': msg_from,
                        'timestamp': message.get('timestamp'),
                        'text': msg_text,
                        'message_id': msg_id
                    })
                
                # Processar status
                statuses = value.get('statuses', [])
                print(f"[WEBHOOK HANDLER] Status updates encontrados: {len(statuses)}")
                for status_idx, status in enumerate(statuses):
                    status_val = status.get('status')
                    status_id = status.get('id')
                    print(f"[WEBHOOK HANDLER]   - Status {status_idx + 1}: ID={status_id}, Status={status_val}")
                    events.append({
                        'type': 'status_update',
                        'recipient_id': status.get('recipient_id'),
                        'status': status_val,
                        'timestamp': status.get('timestamp'),
                        'message_id': status_id,
                        'error': status.get('errors', [{}])[0] if status.get('errors') else None
                    })
        
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}")
            print(f"[WEBHOOK HANDLER] ❌ Erro ao processar webhook: {str(e)}")
            import traceback
            print(f"[WEBHOOK HANDLER] Stack trace: {traceback.format_exc()}")
        
        print(f"[WEBHOOK HANDLER] Total de eventos processados: {len(events)}")
        print("="*80 + "\n")
        return events
    
    @staticmethod
    def log_webhook_event(data):
        """Salva o evento bruto e entidades principais para consultas futuras."""
        try:
            print('[WEBHOOK HANDLER LOG] Persistindo webhook no banco de dados')
            logger.info('[WEBHOOK HANDLER LOG] Salvando webhook event no banco')

            event = WhatsAppWebhookEvent.objects.create(
                object_type=data.get('object', ''),
                payload=data,
            )

            for entry_idx, entry_payload in enumerate(data.get('entry', [])):
                entry = WhatsAppWebhookEntry.objects.create(
                    event=event,
                    entry_index=entry_idx,
                    entry_id=str(entry_payload.get('id', '')),
                    payload=entry_payload,
                )

                for change_idx, change_payload in enumerate(entry_payload.get('changes', [])):
                    value = change_payload.get('value', {})
                    metadata = value.get('metadata', {})
                    change = WhatsAppWebhookChange.objects.create(
                        entry=entry,
                        change_index=change_idx,
                        field=change_payload.get('field', ''),
                        messaging_product=value.get('messaging_product', ''),
                        display_phone_number=metadata.get('display_phone_number', ''),
                        phone_number_id=metadata.get('phone_number_id', ''),
                        payload=change_payload,
                    )

                    for contact_idx, contact_payload in enumerate(value.get('contacts', [])):
                        WhatsAppWebhookContact.objects.create(
                            change=change,
                            contact_index=contact_idx,
                            wa_id=str(contact_payload.get('wa_id', '')),
                            profile_name=contact_payload.get('profile', {}).get('name', ''),
                            payload=contact_payload,
                        )

                    for message_idx, message_payload in enumerate(value.get('messages', [])):
                        text_content = (message_payload.get('text') or {}).get('body', '')
                        msg_timestamp = message_payload.get('timestamp')
                        webhook_message = WhatsAppWebhookMessage.objects.create(
                            change=change,
                            message_index=message_idx,
                            whatsapp_message_id=message_payload.get('id', ''),
                            from_wa_id=message_payload.get('from', ''),
                            message_type=message_payload.get('type', ''),
                            timestamp=int(msg_timestamp) if msg_timestamp else None,
                            text_body=text_content,
                            payload=message_payload,
                        )

                        msg_type = str(message_payload.get('type') or '').lower()
                        if MediaTypeRegistry.is_supported(msg_type):
                            media_config = MediaTypeRegistry.get(msg_type)
                            media_payload_key = media_config.payload_key
                            media_payload = message_payload.get(media_payload_key) or {}
                            
                            logger.info(
                                '[WEBHOOK MEDIA] Mensagem de mídia detectada message_id=%s media_type=%s media_id=%s mime_type=%s',
                                webhook_message.whatsapp_message_id,
                                msg_type,
                                media_payload.get('id'),
                                media_payload.get('mime_type'),
                            )
                            
                            # Extrair filename se documento
                            filename_hint = media_payload.get('filename') if media_config.supports_filename else None
                            
                            media_asset = WhatsAppMediaAsset.objects.create(
                                webhook_message=webhook_message,
                                whatsapp_message_id=webhook_message.whatsapp_message_id,
                                media_id=str(media_payload.get('id') or '').strip(),
                                media_type=msg_type,
                                mime_type=str(media_payload.get('mime_type') or '').strip(),
                                sha256=str(media_payload.get('sha256') or '').strip(),
                                status='pending',
                                payload=media_payload,
                            )
                            logger.info(
                                '[WEBHOOK MEDIA] Asset criado id=%s message_id=%s media_type=%s',
                                media_asset.id,
                                media_asset.whatsapp_message_id,
                                msg_type,
                            )
                            WebhookHandlerService._download_and_store_media_asset(media_asset, media_payload, change)

                    for status_payload in value.get('statuses', []):
                        WebhookHandlerService._update_outbound_status(status_payload, change)

            print(f'[WEBHOOK HANDLER LOG] OK Evento {event.id} registrado com sucesso')
        except Exception as e:
            logger.error(f"Erro ao registrar webhook: {str(e)}")
            print(f"[WEBHOOK HANDLER LOG] ERRO ao registrar evento: {str(e)}")
