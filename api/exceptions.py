"""
Exceções customizadas para o sistema de email.
"""


class EmailServiceError(Exception):
    """Exceção base para erros do serviço de email."""
    pass


class RateLimitExceeded(EmailServiceError):
    """Exceção para indicar que o limite de taxa de envio de emails foi excedido."""
    pass


class DailyLimitExceeded(EmailServiceError):
    """Exceção para indicar que o limite de envios diário foi atingido"""
    pass
