"""Serviços de Notificações (WhatsApp, Webhooks, etc)."""

import os
import requests
import logging
import json

from .models import (
    WhatsAppWebhookEvent,
    WhatsAppWebhookEntry,
    WhatsAppWebhookChange,
    WhatsAppWebhookContact,
    WhatsAppWebhookMessage,
)

logger = logging.getLogger(__name__)


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


class WebhookHandlerService:
    """Serviço para processar webhooks."""
    
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
                        WhatsAppWebhookMessage.objects.create(
                            change=change,
                            message_index=message_idx,
                            whatsapp_message_id=message_payload.get('id', ''),
                            from_wa_id=message_payload.get('from', ''),
                            message_type=message_payload.get('type', ''),
                            timestamp=int(msg_timestamp) if msg_timestamp else None,
                            text_body=text_content,
                            payload=message_payload,
                        )

            print(f'[WEBHOOK HANDLER LOG] OK Evento {event.id} registrado com sucesso')
        except Exception as e:
            logger.error(f"Erro ao registrar webhook: {str(e)}")
            print(f"[WEBHOOK HANDLER LOG] ERRO ao registrar evento: {str(e)}")
