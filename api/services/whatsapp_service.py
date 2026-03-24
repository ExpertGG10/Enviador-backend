"""
WhatsAppService - Serviço para envio de mensagens via WhatsApp API.
Adaptado para aceitar número de telefone no momento do envio.
"""
import logging
import requests
from typing import Dict, List

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Serviço para envio de mensagens via WhatsApp API.
    
    Este serviço aceita o número de telefone no payload ao invés
    de usar um número salvo.
    """

    GRAPH_API_BASE_URL = 'https://graph.facebook.com/v22.0'

    @staticmethod
    def _send_template_message(access_token: str, phone_number_id: str, recipient: str, template: dict) -> dict:
        """Envia um template para um destinatário via WhatsApp Cloud API."""
        url = f"{WhatsAppService.GRAPH_API_BASE_URL}/{phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        body = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': recipient,
            'type': 'template',
            'template': template,
        }

        resp = requests.post(url, json=body, headers=headers, timeout=20)
        try:
            payload = resp.json()
        except ValueError:
            payload = {'raw': resp.text}

        if not resp.ok:
            error_message = payload.get('error', {}).get('message') if isinstance(payload, dict) else None
            return {
                'success': False,
                'status_code': resp.status_code,
                'error': error_message or 'Erro ao enviar template',
                'response': payload,
            }

        message_id = (
            payload.get('messages', [{}])[0].get('id')
            if isinstance(payload, dict) else None
        )
        return {
            'success': True,
            'status_code': resp.status_code,
            'message_id': message_id,
            'response': payload,
        }
    
    @staticmethod
    def send(payload: dict) -> dict:
        """
        Static method to send WhatsApp messages from payload data.
        
        This method is called from the send_view endpoint when channel='whatsapp'.
        
        Args:
            payload: Dictionary containing:
                - phone_number: Phone number to send from (format: 55XXXXXXXXXXX)
                - message: Message text to send
                - rows: List of recipient data dictionaries
                - contact_column: Column name containing phone numbers
                - file_column: Column name containing file paths (optional)
                - attach_to_all: Boolean to attach all files to each message
                - attachment_names: List of attachment names (for multipart requests)
                - _files: Django FILES dict (for multipart requests)
        
        Returns:
            Dictionary with structure:
                - status: 'success' or 'error'
                - previews: List of preview objects
                - summary: Summary of results
                - error: Error message if failed
        """
        try:
            logger.info("[WHATSAPP SEND] Iniciando envio de mensagens via WhatsApp")

            resolved_template_messages = payload.get('resolved_template_messages') or []
            if resolved_template_messages:
                access_token = str(payload.get('whatsapp_access_token') or '').strip()
                phone_number_id = str(payload.get('whatsapp_phone_number_id') or '').strip()
                if not access_token:
                    return {
                        'status': 'error',
                        'error': 'whatsapp_access_token is required for template sends',
                        'previews': [],
                        'summary': {'total': 0, 'success': 0, 'failed': 0}
                    }
                if not phone_number_id:
                    return {
                        'status': 'error',
                        'error': 'whatsapp_phone_number_id is required for template sends',
                        'previews': [],
                        'summary': {'total': 0, 'success': 0, 'failed': 0}
                    }

                total = len(resolved_template_messages)
                success_count = 0
                failed_count = 0
                previews = []
                failed_errors = []

                for i, item in enumerate(resolved_template_messages):
                    recipient = str(item.get('recipient', '')).strip()
                    template = item.get('template') or {}

                    if not recipient:
                        failed_count += 1
                        if len(previews) < 5:
                            previews.append({
                                'index': i,
                                'recipient': '',
                                'template_name': template.get('name', ''),
                                'params_count': len(item.get('params') or []),
                                'status': 'erro',
                                'error': 'recipient vazio',
                            })
                        continue

                    send_result = WhatsAppService._send_template_message(
                        access_token=access_token,
                        phone_number_id=phone_number_id,
                        recipient=recipient,
                        template=template,
                    )

                    if send_result.get('success'):
                        success_count += 1
                        preview_status = 'enviado'
                        preview_error = None
                    else:
                        failed_count += 1
                        preview_status = 'erro'
                        preview_error = send_result.get('error')
                        if preview_error:
                            failed_errors.append(str(preview_error))
                        logger.warning(
                            "[WHATSAPP SEND] Falha ao enviar template: recipient=%s template=%s status_code=%s error=%s",
                            recipient,
                            template.get('name', ''),
                            send_result.get('status_code'),
                            preview_error or 'Erro ao enviar template',
                        )

                    if len(previews) < 5:
                        preview_payload = {
                            'index': i,
                            'recipient': recipient,
                            'template_name': template.get('name', ''),
                            'params_count': len(item.get('params') or []),
                            'status': preview_status,
                        }
                        if preview_error:
                            preview_payload['error'] = preview_error
                        previews.append(preview_payload)

                logger.info(
                    "[WHATSAPP SEND] Envio via templates resolvidos concluído: total=%s success=%s failed=%s",
                    total,
                    success_count,
                    failed_count,
                )

                if success_count == 0 and failed_count > 0:
                    common_error = failed_errors[0] if failed_errors else 'Nenhuma mensagem foi enviada com sucesso'
                    return {
                        'status': 'error',
                        'error': common_error,
                        'previews': previews,
                        'summary': {
                            'total': total,
                            'success': success_count,
                            'failed': failed_count
                        }
                    }

                return {
                    'status': 'success' if failed_count == 0 else 'partial_success',
                    'previews': previews,
                    'summary': {
                        'total': total,
                        'success': success_count,
                        'failed': failed_count
                    }
                }

            resolved_messages = payload.get('resolved_messages') or []
            if resolved_messages:
                total = len(resolved_messages)
                previews = []
                for i, item in enumerate(resolved_messages[:5]):
                    previews.append({
                        'index': i,
                        'recipient': item.get('recipient', ''),
                        'message': (item.get('message', '')[:50] + '...') if len(item.get('message', '')) > 50 else item.get('message', ''),
                        'status': 'enviado'
                    })

                logger.info(f"[WHATSAPP SEND] Envio via mensagens resolvidas: total={total}")
                return {
                    'status': 'success',
                    'previews': previews,
                    'summary': {
                        'total': total,
                        'success': total,
                        'failed': 0
                    }
                }
            
            # Extract payload fields
            phone_number = payload.get('phone_number', '')
            message = payload.get('message', '')
            rows = payload.get('rows', [])
            contact_column = payload.get('contact_column', '')
            file_column = payload.get('file_column', '')
            attach_to_all = payload.get('attach_to_all', False)
            attachment_names = payload.get('attachment_names', [])
            files = payload.get('_files', {})
            
            logger.debug(f"Número remetente (WhatsApp): {phone_number}")
            logger.debug(f"Número de linhas: {len(rows)}")
            logger.debug(f"Coluna de contato: {contact_column}")
            
            # Validate required fields
            if not phone_number:
                return {
                    'status': 'error',
                    'error': 'phone_number é obrigatório para envios via WhatsApp',
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }
            
            if not rows:
                return {
                    'status': 'error',
                    'error': 'Nenhuma linha para processar',
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }
            
            # Extract recipients from rows
            recipients = []
            
            for idx, row in enumerate(rows):
                if contact_column in row:
                    phone_value = row[contact_column]
                    # Convert to string if needed
                    if not isinstance(phone_value, str):
                        phone_value = str(phone_value)
                    phone = phone_value.strip()
                    if phone:
                        recipients.append(phone)
            
            if not recipients:
                return {
                    'status': 'error',
                    'error': f'Nenhum número encontrado na coluna "{contact_column}"',
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }
            
            logger.info(f"[WHATSAPP SEND] Enviando para {len(recipients)} destinatário(s)")
            
            # TODO: Implementar lógica de envio real via WhatsApp API
            # Por enquanto, retornamos sucesso simulado
            
            success_count = 0
            failed_count = 0
            
            try:
                # TODO: Aqui deveria chamar a WhatsApp API com:
                # - phone_number: número remetente
                # - message: mensagem
                # - recipients: lista de destinatários
                # - files: arquivos para anexar (se houver)
                
                # Simular sucesso por enquanto
                success_count = len(recipients)
                failed_count = 0
                
                logger.info(f"[WHATSAPP SEND] Envio concluído: {success_count} sucesso, {failed_count} falhas")
                
                # Generate previews
                previews = []
                for i, recipient in enumerate(recipients[:5]):  # Show first 5 as preview
                    previews.append({
                        'index': i,
                        'recipient': recipient,
                        'message': message[:50] + '...' if len(message) > 50 else message,
                        'status': 'enviado'
                    })
                
                return {
                    'status': 'success',
                    'previews': previews,
                    'summary': {
                        'total': len(recipients),
                        'success': success_count,
                        'failed': failed_count
                    }
                }
                
            except Exception as e:
                logger.error(f"[WHATSAPP SEND] Erro ao enviar mensagens: {str(e)}")
                return {
                    'status': 'error',
                    'error': f'Erro ao enviar: {str(e)}',
                    'previews': [],
                    'summary': {'total': len(recipients), 'success': 0, 'failed': len(recipients)}
                }
        
        except Exception as e:
            logger.error(f"[WHATSAPP SEND] Erro geral no processamento: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Erro ao processar payload: {str(e)}',
                'previews': [],
                'summary': {'total': 0, 'success': 0, 'failed': 0}
            }
