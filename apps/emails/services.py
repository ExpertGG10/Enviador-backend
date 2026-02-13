"""Serviços de Emails."""

import smtplib
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Callable
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from .models import EmailLog
from .utils import EmailBuilder
from apps.senders.models import Sender
from apps.senders.services import AppPasswordService
from core.exceptions import EmailServiceError, RateLimitExceeded, DailyLimitExceeded

logger = logging.getLogger(__name__)


class EmailSendService:
    """Serviço para envio de emails via SMTP.
    
    Adaptado do padrão EmailController do aplicativo desktop,
    mantendo compatibilidade com retry logic e rate limiting detection.
    """
    
    # Configuração SMTP
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465
    
    # Retry logic
    MAX_RETRIES = 5
    RETRY_DELAY = 100  # segundos
    
    # Gmail error codes
    GMAIL_RATE_LIMIT_CODES = ['4.2.1', '4.7.0']  # Too many connections / Access denied
    GMAIL_DAILY_LIMIT_CODES = ['5.4.5', '4.5.4']  # Too many messages / Service unavailable
    
    def __init__(self, sender: Sender):
        """
        Inicializar serviço de email.
        
        Args:
            sender: Objeto Sender (conta de email)
        """
        self.sender = sender
        self.smtp_server: Optional[smtplib.SMTP_SSL] = None
        self._app_password: Optional[str] = None
    
    def _get_app_password(self) -> str:
        """Obter senha de app descriptografada."""
        if not self._app_password:
            self._app_password = AppPasswordService.get_app_password(self.sender)
        return self._app_password
    
    def _connect(self) -> None:
        """Conectar ao servidor SMTP."""
        try:
            if self.smtp_server:
                return  # Já conectado
            
            logger.debug(f"Conectando ao {self.SMTP_HOST}:{self.SMTP_PORT}")
            self.smtp_server = smtplib.SMTP_SSL(
                self.SMTP_HOST,
                self.SMTP_PORT,
                timeout=10
            )
            
            app_password = self._get_app_password()
            self.smtp_server.login(self.sender.email, app_password)
            logger.info(f"Conectado e autenticado como {self.sender.email}")
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erro de autenticação SMTP: {str(e)}")
            raise EmailServiceError(f"Erro de autenticação: Verificar email/senha")
        
        except smtplib.SMTPException as e:
            logger.error(f"Erro SMTP: {str(e)}")
            raise EmailServiceError(f"Erro ao conectar SMTP: {str(e)}")
        
        except Exception as e:
            logger.error(f"Erro desconhecido na conexão SMTP: {str(e)}")
            raise EmailServiceError(f"Erro ao conectar: {str(e)}")
    
    def _parse_smtp_error(self, error_str: str) -> str:
        """Extrair código de erro SMTP da mensagem."""
        # Erro SMTP geralmente é: (code, message)
        # Exemplo: "421 Service not available"
        try:
            parts = error_str.split()
            if parts and parts[0].isdigit():
                return parts[0]
        except:
            pass
        return ""
    
    def _detect_rate_limit(self, error_str: str) -> bool:
        """Detectar se o erro é rate limit."""
        for code in self.GMAIL_RATE_LIMIT_CODES:
            if code in error_str:
                return True
        return False
    
    def _detect_daily_limit(self, error_str: str) -> bool:
        """Detectar se o erro é limite diário excedido."""
        for code in self.GMAIL_DAILY_LIMIT_CODES:
            if code in error_str:
                return True
        return False
    
    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        is_html: bool = True
    ) -> Dict[str, any]:
        """
        Enviar email individual com retry logic.
        
        Adaptado do padrão desktop EmailController.send_email().
        
        Args:
            recipient_email: Email do destinatário
            subject: Assunto
            body: Corpo da mensagem
            attachments: Lista de caminhos de arquivos (opcional)
            is_html: Se body é HTML (padrão: True)
        
        Returns:
            Dict com:
            {
                'success': bool,
                'recipient': str,
                'subject': str,
                'attempts': int,
                'error': str (opcional)
            }
        """
        attempt = 0
        last_error: Optional[Exception] = None
        
        while attempt < self.MAX_RETRIES:
            attempt += 1
            try:
                # Conectar se necessário
                if not self.smtp_server:
                    self._connect()
                
                # Construir mensagem usando EmailBuilder
                builder = EmailBuilder(
                    sender_email=self.sender.email,
                    sender_name=self.sender.name or self.sender.email,
                    is_html=is_html
                )
                
                msg = builder.set_subject(subject)\
                    .set_body(body)\
                    .set_recipients([recipient_email])\
                    .build()
                
                # Se houver anexos, adicionar manualmente (não usar builder para estes)
                if attachments:
                    for attachment_path in attachments:
                        builder.add_attachment(attachment_path)
                    msg = builder.build()
                
                # Enviar
                self.smtp_server.sendmail(
                    self.sender.email,
                    recipient_email,
                    msg.as_string()
                )
                
                logger.info(
                    f"Email enviado com sucesso para {recipient_email} "
                    f"(tentativa {attempt}/{self.MAX_RETRIES})"
                )
                
                return {
                    'success': True,
                    'recipient': recipient_email,
                    'subject': subject,
                    'attempts': attempt,
                    'error': None
                }
            
            except smtplib.SMTPServerDisconnected:
                # Reconectar em caso de desconexão
                logger.warning(f"Conexão SMTP perdida (tentativa {attempt})")
                self.smtp_server = None
                last_error = Exception("Conexão SMTP perdida, tentando reconectar...")
                
                if attempt < self.MAX_RETRIES:
                    time.sleep(5)  # Esperar 5s antes de reconectar
            
            except smtplib.SMTPException as smtp_error:
                error_str = str(smtp_error)
                logger.warning(
                    f"Erro SMTP ao enviar para {recipient_email} "
                    f"(tentativa {attempt}/{self.MAX_RETRIES}): {error_str}"
                )
                
                last_error = smtp_error
                
                # Detectar tipo de erro
                if self._detect_rate_limit(error_str):
                    logger.warning(f"Rate limit detectado. Aguardando {self.RETRY_DELAY}s...")
                    if attempt < self.MAX_RETRIES:
                        time.sleep(self.RETRY_DELAY)
                    else:
                        return {
                            'success': False,
                            'recipient': recipient_email,
                            'subject': subject,
                            'attempts': attempt,
                            'error': f"Rate limit excedido após {self.MAX_RETRIES} tentativas"
                        }
                
                elif self._detect_daily_limit(error_str):
                    logger.error(f"Limite diário de envios excedido")
                    return {
                        'success': False,
                        'recipient': recipient_email,
                        'subject': subject,
                        'attempts': attempt,
                        'error': "Limite diário de envios Gmail excedido"
                    }
                
                else:
                    # Outro erro SMTP
                    if attempt < self.MAX_RETRIES:
                        wait_time = min(5 * attempt, 30)  # Exponential backoff, max 30s
                        logger.warning(f"Tentando novamente em {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        return {
                            'success': False,
                            'recipient': recipient_email,
                            'subject': subject,
                            'attempts': attempt,
                            'error': f"Falha após {self.MAX_RETRIES} tentativas: {error_str}"
                        }
            
            except Exception as e:
                logger.error(
                    f"Erro inesperado ao enviar para {recipient_email}: {str(e)}"
                )
                last_error = e
                
                if attempt < self.MAX_RETRIES:
                    time.sleep(5)
        
        # Se chegou aqui, esgotou tentativas
        error_msg = f"Falha após {self.MAX_RETRIES} tentativas"
        if last_error:
            error_msg = f"{error_msg}: {str(last_error)}"
        
        return {
            'success': False,
            'recipient': recipient_email,
            'subject': subject,
            'attempts': attempt,
            'error': error_msg
        }
    
    def send_mass_emails(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        is_html: bool = True,
        progress_callback: Optional[Callable[[int, Dict], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, any]:
        """
        Enviar emails em massa.
        
        Adaptado do padrão desktop EmailController.send_mass_emails().
        
        Args:
            recipients: Lista de emails para enviar
            subject: Assunto
            body: Corpo da mensagem
            attachments: Lista de caminhos de arquivos (opcional)
            is_html: Se body é HTML
            progress_callback: Callback para progresso (atual, resultado)
            cancel_check: Callback para verificar cancelamento
        
        Returns:
            Dict com estatísticas:
            {
                'total': int,
                'success': int,
                'failed': int,
                'canceled': bool,
                'results': [...]  # Detalhes de cada envio
            }
        """
        if not recipients:
            raise ValueError("Lista de destinatários vazia")
        
        try:
            self._connect()
        except EmailServiceError as e:
            return {
                'total': len(recipients),
                'success': 0,
                'failed': len(recipients),
                'canceled': False,
                'results': [],
                'error': str(e)
            }
        
        success_count = 0
        failed_count = 0
        results = []
        
        for current, recipient in enumerate(recipients, 1):
            # Verificar cancelamento
            if cancel_check and cancel_check():
                logger.info("Envio em massa cancelado pelo usuário")
                return {
                    'total': len(recipients),
                    'success': success_count,
                    'failed': failed_count,
                    'canceled': True,
                    'results': results
                }
            
            # Enviar email
            result = self.send_email(
                recipient_email=recipient,
                subject=subject,
                body=body,
                attachments=attachments,
                is_html=is_html
            )
            
            results.append(result)
            
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
            
            # Callback de progresso
            if progress_callback:
                progress_callback(current, result)
            
            logger.info(
                f"Progresso: {current}/{len(recipients)} "
                f"({success_count} sucesso, {failed_count} falha)"
            )
        
        return {
            'total': len(recipients),
            'success': success_count,
            'failed': failed_count,
            'canceled': False,
            'results': results
        }
    
    def close(self) -> None:
        """Fechar conexão SMTP."""
        if self.smtp_server:
            try:
                self.smtp_server.quit()
                logger.debug("Conexão SMTP fechada")
            except Exception as e:
                logger.warning(f"Erro ao fechar SMTP: {str(e)}")
            finally:
                self.smtp_server = None


class EmailLogService:
    """Serviço para gerenciamento de histórico de envios."""
    
    @staticmethod
    def create_log(user, recipient_email, subject, sender=None, status='queued'):
        """
        Criar registro de envio no histórico.
        
        Returns:
            EmailLog instance
        """
        return EmailLog.objects.create(
            user=user,
            recipient_email=recipient_email,
            subject=subject,
            sender=sender,
            status=status
        )
    
    @staticmethod
    def update_log_sent(log_entry):
        """Marcar como enviado com sucesso."""
        log_entry.status = 'sent'
        log_entry.sent_at = datetime.now()
        log_entry.save()
    
    @staticmethod
    def update_log_failed(log_entry, error_message):
        """Marcar como falhado e adicionar mensagem de erro."""
        log_entry.status = 'failed'
        log_entry.error_message = error_message
        log_entry.attempts += 1
        log_entry.save()
    
    @staticmethod
    def get_user_logs(user, status=None, limit=100):
        """Obter histórico do usuário."""
        logs = EmailLog.objects.filter(user=user)
        if status:
            logs = logs.filter(status=status)
        return logs[:limit]
    
    @staticmethod
    def get_sender_stats(sender):
        """Obter estatísticas de envio da conta."""
        total = EmailLog.objects.filter(sender=sender).count()
        sent = EmailLog.objects.filter(sender=sender, status='sent').count()
        failed = EmailLog.objects.filter(sender=sender, status='failed').count()
        
        return {
            'total': total,
            'sent': sent,
            'failed': failed,
            'success_rate': (sent / total * 100) if total > 0 else 0
        }

