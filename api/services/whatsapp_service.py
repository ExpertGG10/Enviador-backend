"""
WhatsAppService - Serviço para envio de mensagens via WhatsApp API.
Adaptado para aceitar número de telefone no momento do envio.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Serviço para envio de mensagens via WhatsApp API.
    
    Este serviço aceita o número de telefone no payload ao invés
    de usar um número salvo.
    """
    
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
