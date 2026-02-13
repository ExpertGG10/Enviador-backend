"""Views da app de Emails."""

import logging
from typing import List, Dict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
)
from rest_framework.permissions import IsAuthenticated

from .models import EmailLog
from .serializers import EmailLogSerializer
from .services import EmailLogService, EmailSendService
from apps.senders.models import Sender
from apps.senders.services import AppPasswordService
from core.exceptions import EmailServiceError

logger = logging.getLogger(__name__)


class EmailHistoryListView(APIView):
    """Listar histórico de envios de email."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/emails/history/ - Listar histórico do usuário."""
        limit = request.query_params.get('limit', 100)
        status = request.query_params.get('status', None)
        
        logs = EmailLogService.get_user_logs(
            request.user,
            status=status,
            limit=int(limit)
        )
        
        serializer = EmailLogSerializer(logs, many=True)
        return Response(serializer.data, status=HTTP_200_OK)


class EmailSendView(APIView):
    """Enviar emails (endpoint principal)."""
    permission_classes = [IsAuthenticated]
    
    def _extract_recipient_emails(self, recipients: List[Dict]) -> List[str]:
        """Extrair lista de emails dos recipients."""
        emails = []
        for recipient in recipients:
            if isinstance(recipient, dict):
                email = recipient.get('email')
            else:
                email = str(recipient)
            
            if email and '@' in email:
                emails.append(email)
        
        return emails
    
    def _create_email_logs(self, user, recipients: List[str], subject: str, sender: Sender) -> List[EmailLog]:
        """Criar registros de log para cada destinatário."""
        logs = []
        for recipient_email in recipients:
            log = EmailLogService.create_log(
                user=user,
                recipient_email=recipient_email,
                subject=subject,
                sender=sender,
                status='queued'
            )
            logs.append(log)
        return logs
    
    def post(self, request):
        """
        POST /api/emails/send/
        
        Body:
        {
            "sender_id": 1,
            "app_password": "senha_de_app_opcional",
            "recipients": [
                {"email": "user@example.com"},
                {"email": "user2@example.com"}
            ],
            "subject": "Assunto",
            "body": "<html>...</html>",
            "is_html": true,
            "attachments": [],
            "send_async": false
        }
        
        Response:
        {
            "total": 2,
            "success": 2,
            "failed": 0,
            "results": [...]
        }
        """
        # Extração de dados
        sender_id = request.data.get('sender_id')
        app_password = request.data.get('app_password', '').strip()
        recipients = request.data.get('recipients', [])
        subject = request.data.get('subject', '').strip()
        body = request.data.get('body', '').strip()
        is_html = request.data.get('is_html', True)
        attachments = request.data.get('attachments', [])
        send_async = request.data.get('send_async', False)
        
        # Validações
        if not sender_id:
            return Response(
                {'error': 'sender_id é obrigatório'},
                status=HTTP_400_BAD_REQUEST
            )
        
        if not recipients:
            return Response(
                {'error': 'recipients não pode estar vazio'},
                status=HTTP_400_BAD_REQUEST
            )
        
        if not subject:
            return Response(
                {'error': 'subject é obrigatório'},
                status=HTTP_400_BAD_REQUEST
            )
        
        if not body:
            return Response(
                {'error': 'body é obrigatório'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Obter conta remetente
        try:
            sender = Sender.objects.get(id=sender_id, user=request.user)
        except Sender.DoesNotExist:
            return Response(
                {'error': 'Conta remetente não encontrada'},
                status=HTTP_404_NOT_FOUND
            )
        
        # Verificar se tem senha configurada ou se foi informada
        if not app_password and not AppPasswordService.has_app_password(sender):
            return Response(
                {'error': 'Nenhuma senha de aplicativo fornecida. Informe app_password no request ou configure previamente.'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Se senha foi fornecida, atualizar temporariamente (apenas para este envio)
        if app_password:
            AppPasswordService.set_app_password(sender, app_password)
        
        # Extrair emails válidos
        recipient_emails = self._extract_recipient_emails(recipients)
        if not recipient_emails:
            return Response(
                {'error': 'Nenhum email válido nos destinatários'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Criar logs de envio
        email_logs = self._create_email_logs(
            request.user,
            recipient_emails,
            subject,
            sender
        )
        
        if send_async:
            # TODO: Integrar com Celery/Redis para envio assíncrono
            # Por enquanto, apenas retornar como aceito
            return Response({
                'message': f'{len(email_logs)} email(s) enfileirado(s) para envio assíncrono',
                'total': len(email_logs),
                'log_ids': [log.id for log in email_logs]
            }, status=HTTP_202_ACCEPTED)
        
        # Envio síncrono (para testes e uso imediato)
        try:
            email_service = EmailSendService(sender)
            
            def progress_callback(current: int, result: Dict):
                """Callback de progresso - atualizar logs."""
                log = email_logs[current - 1]
                if result['success']:
                    EmailLogService.update_log_sent(log)
                else:
                    EmailLogService.update_log_failed(log, result['error'])
            
            send_result = email_service.send_mass_emails(
                recipients=recipient_emails,
                subject=subject,
                body=body,
                attachments=attachments if attachments else None,
                is_html=is_html,
                progress_callback=progress_callback
            )
            
            email_service.close()
            
            return Response({
                'total': send_result['total'],
                'success': send_result['success'],
                'failed': send_result['failed'],
                'canceled': send_result['canceled'],
                'results': send_result['results']
            }, status=HTTP_200_OK)
        
        except EmailServiceError as e:
            logger.error(f"Erro no serviço de email: {str(e)}")
            
            # Marcar todos os logs como falhas
            for log in email_logs:
                EmailLogService.update_log_failed(log, str(e))
            
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar emails: {str(e)}", exc_info=True)
            
            # Marcar todos os logs como falhas
            for log in email_logs:
                EmailLogService.update_log_failed(log, f"Erro inesperado: {str(e)}")
            
            return Response(
                {'error': f'Erro ao processar envio: {str(e)}'},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailStatsView(APIView):
    """Estatísticas de envio de emails."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, sender_id):
        """GET /api/emails/stats/{sender_id}/"""
        try:
            sender = Sender.objects.get(id=sender_id, user=request.user)
        except Sender.DoesNotExist:
            return Response(
                {'error': 'Conta remetente não encontrada'},
                status=HTTP_404_NOT_FOUND
            )
        
        stats = EmailLogService.get_sender_stats(sender)
        return Response(stats, status=HTTP_200_OK)

