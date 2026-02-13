"""
EmailService - Controlador de envio de emails via SMTP.
Reutilizado fielmente de Enviador_de_Email/controller/email_controller.py
Adaptado para Django models.
"""
import os
import sys
import smtplib
import mimetypes
import logging
import time
import re
import json
from io import BytesIO
from email.mime.text import MIMEText

# Importar EmailModel diretamente do módulo
import importlib.util
spec = importlib.util.spec_from_file_location(
    "email_model",
    os.path.join(os.path.dirname(__file__), '..', 'models', 'email_model.py')
)
email_model_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(email_model_module)
EmailModel = email_model_module.EmailModel

from api.exceptions import DailyLimitExceeded, RateLimitExceeded
from api.utils.crypto import decrypt_password

logger = logging.getLogger(__name__)


class BytesFileWrapper:
    """
    Wrapper para converter dados em bytes em um objeto file-like.
    Usado para converter dicionários de arquivo armazenados em bytes de volta para file-like objects.
    """
    def __init__(self, data: dict):
        """
        Args:
            data: Dicionário com 'name', 'content' e 'size'
        """
        self.name = data.get('name', 'unknown')
        self.size = data.get('size', 0)
        self._content = data.get('content', b'')
        self._file_obj = BytesIO(self._content)
    
    def read(self, size=-1):
        """Ler conteúdo do arquivo"""
        return self._file_obj.read(size)
    
    def seek(self, offset, whence=0):
        """Resetar posição do arquivo"""
        return self._file_obj.seek(offset, whence)
    
    def tell(self):
        """Retornar posição atual"""
        return self._file_obj.tell()


class EmailService:
    """
    Controller que gerencia o envio de emails.

    Args:
        sender: Objeto Sender com detalhes do email
        app_password: Senha de app (não criptografada)
    """
    def __init__(self, sender, app_password: str):
        self.sender = sender
        self.password = app_password
        
        self.smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        self.smtp_server.login(self.sender.email, self.password)

    def send_mass_emails(self, recipients_data: list, progress=None, cancel_check=None) -> dict:
        """
        Send emails in bulk to a list of recipients.
        
        Args:
            recipient_list: List of recipient email addresses
            subject: Subject of the email
            body: Body content of the email (HTML format)
            attachments: List of file paths to attach to the email
            progress: Optional callable to report progress (current, total)
            cancel_check: Optional callable that returns True if sending should be canceled

        Returns:
            A dictionary with counts of total, successful, and failed emails.
        """
        success_count = 0
        failed_count = 0

        try:
            for i, entry in enumerate(recipients_data, 1):
                # entry expected to be dict: {'email','subject','body','attachments'}
                recipient = entry.get('email')
                subject = entry.get('subject')
                body = entry.get('body')
                attachments = entry.get('attachments') if entry.get('attachments') else None
                
                if cancel_check and cancel_check():
                    return {
                        'total': len(recipients_data),
                        'success': success_count,
                        'failed': failed_count,
                        'canceled': True
                    }
                
                attempt = 0
                attempt_limit = 5
                sleep_time = 100

                for j in range(attempt_limit):
                    attempt += 1
                    try:
                        email = EmailModel(self.sender.email, recipient, subject, body, attachments)
                        result = self.send_email(email)
                        
                        if result:
                            success_count += 1
                            # progress callback receives a dict with details
                            if progress:
                                try:
                                    progress({'index': i, 'email': recipient, 'status': 'success', 'message': None})
                                except Exception:
                                    pass
                            break
                    except RateLimitExceeded as rate_err:
                        time.sleep(sleep_time)
                    except DailyLimitExceeded as daily_err:
                        raise DailyLimitExceeded(f"[ERROR] Daily limit exceeded when sending to: {recipient}: {daily_err}")
                    except Exception as e:
                        failed_count += 1
                        # report failure to progress
                        if progress:
                            try:
                                progress({'index': i, 'email': recipient, 'status': 'failed', 'message': str(e)})
                            except Exception:
                                pass
                        raise Exception(f"An error occurred sending email to {recipient}: {e}")
            
            return {
                'total': len(recipients_data),
                'success': success_count,
                'failed': failed_count
            }
        except smtplib.SMTPAuthenticationError:
            raise ValueError("Authentication error! Check the email and app password.")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")

    def send_email(self, email: EmailModel) -> bool:
        """
        Send a single email to a recipient.

        Args:
            email: EmailModel instance containing email details

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        try:
            msg = email.create_message()

            # The EmailModel.create_message() already builds the correct message
            # (including attachments when present). For MIMEMultipart messages
            # we must not call EmailMessage-specific methods like clear_content()
            # which don't exist, otherwise attachments can be lost.
            try:
                # Ensure non-multipart messages have HTML body set
                if not msg.is_multipart():
                    try:
                        msg.set_content(email.body, subtype="html", charset="utf-8")
                    except Exception:
                        # Older EmailMessage implementations may differ; ignore
                        pass

                self.smtp_server.send_message(msg)
            except Exception as send_err:
                raise

            return True
        except smtplib.SMTPAuthenticationError:
            raise ValueError("Authentication error! Check the email and app password.")
        except Exception as e:
            if "4.2.1" in str(e):
                raise RateLimitExceeded()
            elif "5.4.5" in str(e):
                raise DailyLimitExceeded()
            else:
                raise Exception(f"An error occurred: {e}")

    def __del__(self):
        logger.debug("[SMTP] Closing SMTP connection...")
        try:
            self.smtp_server.quit()
        except Exception:
            pass
        logger.debug("[OK] SMTP connection closed")

    @staticmethod
    def send(payload: dict, job_id: str = None) -> dict:
        """
        Static method to send emails from payload data.
        """
        try:
            # Extract payload fields
            email_sender = payload.get('email_sender', '')
            app_password = payload.get('app_password', '')
            subject = payload.get('subject', '')
            message = payload.get('message', '')
            rows = payload.get('rows', [])
            contact_column = payload.get('contact_column', '')
            file_column = payload.get('file_column', '')
            attach_to_all = payload.get('attach_to_all', False)
            attachment_names = payload.get('attachment_names', [])
            files = payload.get('_files', {})
            
            # Validate required fields
            if not email_sender or not app_password:
                error_msg = 'email_sender e app_password são obrigatórios'
                return {
                    'status': 'error',
                    'error': error_msg,
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }
            
            if not rows:
                error_msg = 'Nenhuma linha para processar'
                return {
                    'status': 'error',
                    'error': error_msg,
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }
            
            # Create a simple sender object that mimics the Sender model
            class SimpleSender:
                def __init__(self, email):
                    self.email = email
            
            sender = SimpleSender(email_sender)
            
            # Create EmailService instance
            email_service = EmailService(sender, app_password)
            
            # Build maps of uploaded files for fast lookup by full name and by basename (without extension)
            # helper: normalize names by stripping arrows, whitespace and common extensions
            def _normalize(name: str) -> str:
                if not name:
                    return ''
                s = str(name).strip()
                # remove leading arrows, dashes, bullets and whitespace
                s = re.sub(r'^[\s\-\u2192>»•]+', '', s)
                # strip quotes
                s = s.strip('"\'')
                s = s.strip()
                lower = s.lower()
                # remove common extensions
                lower = re.sub(r'\.(jpg|jpeg|png|gif|pdf|docx|doc|xlsx|xls|zip|txt)$', '', lower, flags=re.IGNORECASE)
                return lower

            attachments_map_by_name = {}
            if files:
                for key, file_list in files.items():
                    for file_data in file_list:
                        if not file_data:
                            continue
                        
                        # Converter dados em bytes para um objeto file-like
                        if isinstance(file_data, dict):
                            uploaded_file = BytesFileWrapper(file_data)
                        else:
                            uploaded_file = file_data
                        
                        fname = getattr(uploaded_file, 'name', None) or str(uploaded_file)
                        
                        # normalize: remove extension and clean up
                        base = os.path.splitext(os.path.basename(fname))[0]
                        norm = _normalize(base)
                        
                        if norm:
                            attachments_map_by_name[norm] = uploaded_file

            # Prepare global attachments (attach to all) if requested
            global_attachments = []
            
            if attach_to_all and files:
                for key, file_list in files.items():
                    for idx, file_data in enumerate(file_list):
                        if file_data:
                            # Converter dados em bytes para um objeto file-like
                            if isinstance(file_data, dict):
                                uploaded_file = BytesFileWrapper(file_data)
                            else:
                                uploaded_file = file_data
                            
                            global_attachments.append(uploaded_file)

            # Build recipients data list with per-recipient subject/body/attachments
            recipients_data = []
            
            for idx, row in enumerate(rows):
                if contact_column not in row:
                    continue
                
                email_value = row[contact_column]
                if not isinstance(email_value, str):
                    email_value = str(email_value)
                email = email_value.strip()
                
                if not email:
                    continue

                # Start from the template subject/message and replace placeholders {Header}
                personalized_subject = subject
                personalized_message = message
                try:
                    for col_key, col_val in row.items():
                        placeholder = '{' + str(col_key) + '}'
                        if placeholder in personalized_subject:
                            personalized_subject = personalized_subject.replace(placeholder, str(col_val))
                        if placeholder in personalized_message:
                            personalized_message = personalized_message.replace(placeholder, str(col_val))
                except Exception:
                    pass

                # Resolve per-row attachments unless attach_to_all
                attachments_for_recipient = None
                if not attach_to_all and file_column and file_column in row:
                    raw_refs = row[file_column]
                    
                    refs = []
                    if isinstance(raw_refs, (list, tuple)):
                        refs = list(raw_refs)
                    elif isinstance(raw_refs, str):
                        # split by common separators
                        for part in raw_refs.split(';'):
                            for p in part.split(','):
                                p = p.strip()
                                if p:
                                    refs.append(p)
                    else:
                        refs = [str(raw_refs)]

                    resolved = []
                    for ref in refs:
                        if not ref:
                            continue
                        key = str(ref).strip()
                        
                        # normalize reference (strip extension, arrows, whitespace)
                        norm_ref = _normalize(key)
                        
                        # Try normalized name match (ignores extensions like .jpg)
                        found = attachments_map_by_name.get(norm_ref)
                        if found:
                            resolved.append(found)
                            continue
                        
                        # Last resort: if the ref looks like a path on disk, include it
                        if os.path.isfile(key):
                            resolved.append(key)

                    if resolved:
                        attachments_for_recipient = resolved
                else:
                    if global_attachments:
                        attachments_for_recipient = global_attachments

                recipients_data.append({
                    'email': email,
                    'subject': personalized_subject,
                    'body': personalized_message,
                    'attachments': attachments_for_recipient
                })
            
            if not recipients_data:
                return {
                    'status': 'error',
                    'error': f'Nenhum email encontrado na coluna "{contact_column}"',
                    'previews': [],
                    'summary': {'total': 0, 'success': 0, 'failed': 0}
                }

            logger.info(f"[SEND] Enviando para {len(recipients_data)} destinatário(s)")

            # Send emails using per-recipient data
            try:
                # If job_id provided, set up progress and cancel callbacks to report into job manager
                if job_id:
                    try:
                        from .job_manager import set_total, update_progress, is_canceled
                        set_total(job_id, len(recipients_data))

                        def _progress(evt):
                            # evt expected to be dict {index,email,status,message}
                            try:
                                update_progress(job_id, index=evt.get('index'), email=evt.get('email'), status=evt.get('status'), message=evt.get('message'))
                            except Exception:
                                pass

                        def _cancel_check():
                            try:
                                return is_canceled(job_id)
                            except Exception:
                                return False

                        results = email_service.send_mass_emails(recipients_data=recipients_data, progress=_progress, cancel_check=_cancel_check)
                    except Exception:
                        # Fallback to plain send if job manager not available
                        results = email_service.send_mass_emails(recipients_data=recipients_data)
                else:
                    results = email_service.send_mass_emails(recipients_data=recipients_data)
                
                logger.info(f"[SEND] Envio concluído: {results['success']} sucesso, {results['failed']} falhas")
                
                # Generate previews
                previews = []
                for i, recipient_entry in enumerate(recipients_data[:5]):  # Show first 5 as preview
                    previews.append({
                        'index': i,
                        'recipient': recipient_entry.get('email'),
                        'subject': recipient_entry.get('subject') or subject,
                        'status': 'enviado' if results['success'] > 0 else 'erro'
                    })
                
                return {
                    'status': 'success',
                    'previews': previews,
                    'summary': {
                        'total': results['total'],
                        'success': results['success'],
                        'failed': results['failed']
                    }
                }
                
            except ValueError as ve:
                logger.error(f"[SEND] Erro de autenticação: {str(ve)}")
                return {
                    'status': 'error',
                    'error': f'Erro de autenticação: {str(ve)}',
                    'previews': [],
                    'summary': {'total': len(recipients_data), 'success': 0, 'failed': len(recipients_data)}
                }
            
            except Exception as e:
                logger.error(f"[SEND] Erro ao enviar emails: {str(e)}")
                return {
                    'status': 'error',
                    'error': f'Erro ao enviar: {str(e)}',
                    'previews': [],
                    'summary': {'total': len(recipients_data), 'success': 0, 'failed': len(recipients_data)}
                }
        
        except Exception as e:
            logger.error(f"[SEND] Erro geral no processamento: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Erro ao processar payload: {str(e)}',
                'previews': [],
                'summary': {'total': 0, 'success': 0, 'failed': 0}
            }
