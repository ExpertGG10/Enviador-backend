"""Serviços de Notificações (WhatsApp, Webhooks, etc)."""

import os
import requests
import logging
import json

logger = logging.getLogger(__name__)


class WhatsAppAPIService:
    """Serviço para integração com API do WhatsApp/Meta."""
    
    BASE_URL = 'https://graph.instagram.com/v18.0'
    
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
    
    def send_text_message(self, to_number: str, message: str):
        """Enviar mensagem de texto simples."""
        try:
            print(f"[WHATSAPP TEXT] Enviando mensagem de texto para: {to_number}")
            print(f"[WHATSAPP TEXT] Conteúdo: {message}")
            logger.info(f"[WHATSAPP TEXT] Enviando texto para: {to_number}")
            url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message}
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
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
        """Log webhook event para auditoria."""
        try:
            print(f"[WEBHOOK HANDLER LOG] Registrando evento de webhook em arquivo de log")
            logger.info(f"[WEBHOOK HANDLER LOG] Salvando webhook event")
            with open('/tmp/webhook_events.log', 'a') as f:
                f.write(f"{json.dumps(data)}\n")
            print(f"[WEBHOOK HANDLER LOG] ✓ Evento registrado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao registrar webhook: {str(e)}")
            print(f"[WEBHOOK HANDLER LOG] ❌ Erro ao registrar evento: {str(e)}")
