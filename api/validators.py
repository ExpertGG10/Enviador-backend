"""
Validadores para o sistema de email.
"""
import re
from typing import List


def validate_email(email: str) -> bool:
    """
    Valida se um email tem formato válido.
    
    Args:
        email: Email a ser validado
        
    Returns:
        bool: True se email é válido
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_file_extension(file_path: str) -> bool:
    """
    Valida se arquivo tem extensão suportada.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        bool: True se extensão é suportada
    """
    supported_extensions = ['.xlsx', '.xls', '.csv']
    return any(file_path.lower().endswith(ext) for ext in supported_extensions)


def validate_required_fields(sender_email: str, recipients: List[str], subject: str, body: str) -> List[str]:
    """
    Valida campos obrigatórios e retorna lista de erros.
    
    Args:
        sender_email: Email do remetente
        recipients: Lista de destinatários
        subject: Assunto
        body: Corpo
        
    Returns:
        List[str]: Lista de mensagens de erro (vazia se válido)
    """
    errors = []

    if not sender_email or not sender_email.strip():
        errors.append("Email do remetente é obrigatório")
    elif not validate_email(sender_email):
        errors.append("Email do remetente inválido")
    
    if not recipients:
        errors.append("Pelo menos um destinatário é obrigatório")
    else:
        invalid_emails = [email for email in recipients if not validate_email(email)]
        if invalid_emails:
            errors.append(f"Emails inválidos encontrados: {', '.join(invalid_emails[:3])}")
    
    if not subject or not subject.strip():
        errors.append("Assunto é obrigatório")
    
    if not body or not body.strip():
        errors.append("Corpo do email é obrigatório")
    
    return errors
