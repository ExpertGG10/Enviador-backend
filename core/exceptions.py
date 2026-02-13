"""Exceções globais da aplicação."""


class AppException(Exception):
    """Exceção base da aplicação."""
    pass


class EmailServiceError(AppException):
    """Erro ao enviar email."""
    pass


class WhatsAppServiceError(AppException):
    """Erro ao enviar mensagem WhatsApp."""
    pass


class RateLimitExceeded(AppException):
    """Limite de taxa de requisição excedido."""
    pass


class DailyLimitExceeded(AppException):
    """Limite diário de envios excedido."""
    pass


class ValidationError(AppException):
    """Erro de validação."""
    pass


class NotFoundError(AppException):
    """Recurso não encontrado."""
    pass
