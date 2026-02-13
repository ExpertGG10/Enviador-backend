"""Utilitários para construção e gerenciamento de emails."""

import os
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email import encoders
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EmailBuilder:
    """Construtor de mensagens de email com suporte a anexos.
    
    Adaptado do padrão EmailModel do aplicativo desktop.
    """
    
    # MIME types suportados
    SUPPORTED_ATTACHMENTS = {
        'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
        'document': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'],
        'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
        'video': ['mp4', 'avi', 'mov', 'mkv', 'flv'],
        'audio': ['mp3', 'wav', 'aac', 'flac', 'ogg']
    }
    
    # Limite de tamanho: 25MB (Gmail limit)
    MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024
    
    def __init__(
        self,
        sender_email: str,
        sender_name: Optional[str] = None,
        is_html: bool = False
    ):
        """
        Inicializar construtor de email.
        
        Args:
            sender_email: Email do remetente
            sender_name: Nome do remetente (opcional)
            is_html: Se o corpo é HTML (padrão: False)
        """
        self.sender_email = sender_email
        self.sender_name = sender_name or sender_email.split('@')[0]
        self.is_html = is_html
        self.subject: Optional[str] = None
        self.body: Optional[str] = None
        self.recipients: List[str] = []
        self.cc_recipients: List[str] = []
        self.bcc_recipients: List[str] = []
        self.attachments: List[Dict[str, Any]] = []
    
    def set_recipients(self, recipients: List[str]) -> 'EmailBuilder':
        """Definir destinatários (To)."""
        self.recipients = recipients if isinstance(recipients, list) else [recipients]
        return self
    
    def add_recipient(self, recipient: str) -> 'EmailBuilder':
        """Adicionar um destinatário."""
        if recipient not in self.recipients:
            self.recipients.append(recipient)
        return self
    
    def set_cc(self, cc_recipients: List[str]) -> 'EmailBuilder':
        """Definir cópia (CC)."""
        self.cc_recipients = cc_recipients if isinstance(cc_recipients, list) else [cc_recipients]
        return self
    
    def add_cc(self, recipient: str) -> 'EmailBuilder':
        """Adicionar cópia (CC)."""
        if recipient not in self.cc_recipients:
            self.cc_recipients.append(recipient)
        return self
    
    def set_bcc(self, bcc_recipients: List[str]) -> 'EmailBuilder':
        """Definir cópia oculta (BCC)."""
        self.bcc_recipients = bcc_recipients if isinstance(bcc_recipients, list) else [bcc_recipients]
        return self
    
    def add_bcc(self, recipient: str) -> 'EmailBuilder':
        """Adicionar cópia oculta (BCC)."""
        if recipient not in self.bcc_recipients:
            self.bcc_recipients.append(recipient)
        return self
    
    def set_subject(self, subject: str) -> 'EmailBuilder':
        """Definir assunto."""
        self.subject = subject
        return self
    
    def set_body(self, body: str) -> 'EmailBuilder':
        """Definir corpo da mensagem."""
        self.body = body
        return self
    
    def add_attachment(self, file_path: str) -> 'EmailBuilder':
        """
        Adicionar anexo.
        
        Args:
            file_path: Caminho do arquivo a anexar
            
        Returns:
            self para encadeamento de chamadas
            
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se arquivo não suportado ou muito grande
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_ATTACHMENT_SIZE:
            raise ValueError(
                f"Arquivo muito grande ({file_size / 1024 / 1024:.2f}MB). "
                f"Máximo: {self.MAX_ATTACHMENT_SIZE / 1024 / 1024:.2f}MB"
            )
        
        # Verificar se extensão é suportada
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip('.')
        
        is_supported = any(
            ext in exts for exts in self.SUPPORTED_ATTACHMENTS.values()
        )
        if not is_supported:
            logger.warning(f"Extensão não recomendada: {ext}")
        
        self.attachments.append({
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': file_size
        })
        return self
    
    def add_attachments(self, file_paths: List[str]) -> 'EmailBuilder':
        """Adicionar múltiplos anexos."""
        for file_path in file_paths:
            self.add_attachment(file_path)
        return self
    
    def _get_mime_type(self, file_path: str) -> tuple:
        """Obter MIME type de um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Tupla (maintype, subtype)
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        maintype, subtype = mime_type.split('/', 1)
        return maintype, subtype
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str, file_name: str) -> None:
        """Anexar arquivo à mensagem.
        
        Args:
            msg: Objeto MIMEMultipart
            file_path: Caminho do arquivo
            file_name: Nome do arquivo para aparecer no email
        """
        try:
            maintype, subtype = self._get_mime_type(file_path)
            
            with open(file_path, 'rb') as attachment:
                if maintype == 'text':
                    part = MIMEText(attachment.read().decode('utf-8'), _subtype=subtype)
                elif maintype == 'image':
                    part = MIMEImage(attachment.read(), _subtype=subtype)
                elif maintype == 'audio':
                    part = MIMEAudio(attachment.read(), _subtype=subtype)
                else:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
            
            part.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(part)
            logger.debug(f"Anexo adicionado: {file_name}")
        
        except Exception as e:
            logger.error(f"Erro ao anexar {file_path}: {str(e)}")
            raise
    
    def build(self) -> MIMEMultipart:
        """
        Construir e retornar mensagem MIME.
        
        Returns:
            MIMEMultipart com a mensagem completa
            
        Raises:
            ValueError: Se faltam campos obrigatórios
        """
        if not self.subject:
            raise ValueError("Assunto não definido")
        if not self.body:
            raise ValueError("Corpo não definido")
        if not self.recipients:
            raise ValueError("Pelo menos um destinatário é obrigatório")
        
        # Criar mensagem multipart
        msg = MIMEMultipart('mixed')
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = ', '.join(self.recipients)
        msg['Subject'] = self.subject
        
        if self.cc_recipients:
            msg['Cc'] = ', '.join(self.cc_recipients)
        
        # Adicionar corpo (text/html ou text/plain)
        content_type = 'html' if self.is_html else 'plain'
        msg_body = MIMEText(self.body, _subtype=content_type)
        msg.attach(msg_body)
        
        # Adicionar anexos
        for attachment in self.attachments:
            self._attach_file(
                msg,
                attachment['path'],
                attachment['name']
            )
        
        return msg
    
    def build_string(self) -> str:
        """
        Construir e retornar mensagem como string.
        
        Returns:
            String da mensagem MIME completa
        """
        msg = self.build()
        return msg.as_string()
    
    def get_all_recipients(self) -> List[str]:
        """Obter lista completa de todos os destinatários (To + CC + BCC)."""
        return self.recipients + self.cc_recipients + self.bcc_recipients
    
    def get_attachment_info(self) -> List[Dict[str, Any]]:
        """Obter informações sobre anexos."""
        return self.attachments.copy()
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validar se email está pronto para envio.
        
        Returns:
            Tupla (is_valid, error_message)
        """
        if not self.subject or not self.subject.strip():
            return False, "Assunto não pode estar vazio"
        
        if not self.body or not self.body.strip():
            return False, "Corpo não pode estar vazio"
        
        if not self.recipients:
            return False, "Pelo menos um destinatário é obrigatório"
        
        total_attachment_size = sum(a['size'] for a in self.attachments)
        if total_attachment_size > self.MAX_ATTACHMENT_SIZE:
            return False, (
                f"Tamanho total de anexos excede o limite "
                f"({total_attachment_size / 1024 / 1024:.2f}MB > "
                f"{self.MAX_ATTACHMENT_SIZE / 1024 / 1024:.2f}MB)"
            )
        
        return True, None
    
    def reset(self) -> 'EmailBuilder':
        """Limpar todos os dados para construir novo email."""
        self.subject = None
        self.body = None
        self.recipients = []
        self.cc_recipients = []
        self.bcc_recipients = []
        self.attachments = []
        return self
