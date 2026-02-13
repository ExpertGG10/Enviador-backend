"""
Criptografia de senhas usando Fernet com suporte a Web e Desktop.

Compatível com:
- Web (Django): Usa variáveis de ambiente para chaves mestras
- Desktop: Usa keyring do SO (opcional, via try/except)

Suporta rotação de chaves e múltiplos esquemas de criptografia.
"""

import os
from typing import Optional, Dict
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)

# Configurações
DEFAULT_KEY_ID = "enviador-v1"
DEFAULT_SCHEME = "fernet:v1"
SERVICE_NAME = "enviador_backend"

# Tentando importar keyring (opcional para web)
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.debug("Keyring não disponível - usando variáveis de ambiente")


def get_default_key_id() -> str:
    """Obter ID padrão da chave."""
    return DEFAULT_KEY_ID


def get_default_scheme() -> str:
    """Obter esquema de criptografia padrão."""
    return DEFAULT_SCHEME


def _get_master_key_from_env(key_id: str) -> Optional[bytes]:
    """
    Obter chave mestra de variável de ambiente.
    
    Busca por: ENCRYPTION_KEY_{key_id}
    Exemplo: ENCRYPTION_KEY_enviador-v1
    
    Args:
        key_id: Identificador da chave
    
    Returns:
        bytes: Chave ou None se não encontrada
    """
    env_var = f"ENCRYPTION_KEY_{key_id.upper().replace('-', '_')}"
    key_str = os.environ.get(env_var)
    
    if key_str:
        try:
            return key_str.encode() if isinstance(key_str, str) else key_str
        except Exception as e:
            logger.error(f"Erro ao processar chave do ambiente: {str(e)}")
            return None
    
    return None


def _get_master_key_from_keyring(key_id: str) -> Optional[bytes]:
    """
    Obter chave mestra do keyring do SO (Desktop).
    
    Args:
        key_id: Identificador da chave
    
    Returns:
        bytes: Chave ou None se não disponível
    """
    if not KEYRING_AVAILABLE:
        return None
    
    try:
        key_str = keyring.get_password(SERVICE_NAME, key_id)
        if key_str:
            return key_str.encode()
    except Exception as e:
        logger.warning(f"Falha ao acessar keyring: {str(e)}")
    
    return None


def _get_master_key(key_id: str = None) -> bytes:
    """
    Recuperar chave mestra (Web + Desktop compatible).
    
    Ordem de busca:
    1. Variáveis de ambiente (Web)
    2. Keyring do SO (Desktop)
    3. Erro se não encontrada
    
    Args:
        key_id: Identificador da chave (padrão: DEFAULT_KEY_ID)
    
    Returns:
        bytes: Chave mestra
        
    Raises:
        RuntimeError: Se chave não for encontrada
    """
    key_id = key_id or DEFAULT_KEY_ID
    
    # Tentar ambiente primeiro (web)
    key = _get_master_key_from_env(key_id)
    if key:
        logger.debug(f"Chave '{key_id}' obtida do ambiente")
        return key
    
    # Tentar keyring (desktop)
    key = _get_master_key_from_keyring(key_id)
    if key:
        logger.debug(f"Chave '{key_id}' obtida do keyring")
        return key
    
    # Erro se nenhuma for encontrada
    error_msg = (
        f"Chave mestra '{key_id}' não encontrada. "
        f"Configure ENCRYPTION_KEY_{key_id.upper().replace('-', '_')} "
        "como variável de ambiente."
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def generate_and_store_master_key(key_id: str = None, force: bool = False) -> bytes:
    """
    Gerar e armazenar chave mestra de criptografia.
    
    Para Web: Retorna a chave e exibe instrução para variável de ambiente
    Para Desktop: Armazena no keyring
    
    Args:
        key_id: Identificador da chave (padrão: DEFAULT_KEY_ID)
        force: Forçar regeneração mesmo se existir
    
    Returns:
        bytes: Chave gerada/existente
    """
    key_id = key_id or DEFAULT_KEY_ID
    
    try:
        # Verificar se já existe (a menos que force=True)
        if not force:
            try:
                existing_key = _get_master_key(key_id)
                logger.info(f"Chave '{key_id}' já existe")
                return existing_key
            except RuntimeError:
                pass  # Continuar para gerar nova
        
        # Gerar nova chave
        new_key = Fernet.generate_key()
        key_str = new_key.decode()
        
        # Tentar armazenar no keyring (desktop)
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(SERVICE_NAME, key_id, key_str)
                logger.info(f"Chave '{key_id}' armazenada no keyring com sucesso")
                return new_key
            except Exception as e:
                logger.warning(f"Falha ao armazenar no keyring: {str(e)}")
        
        # Para web: exibir instrução de variável de ambiente
        env_var = f"ENCRYPTION_KEY_{key_id.upper().replace('-', '_')}"
        logger.warning(
            f"Para web, configure a variável de ambiente:\n"
            f"  export {env_var}={key_str}\n"
            f"Ou em .env:\n"
            f"  {env_var}={key_str}"
        )
        
        logger.info(f"Chave '{key_id}' gerada com sucesso")
        return new_key
    
    except Exception as e:
        error_msg = f"Erro ao gerar/armazenar chave mestra: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def encrypt_password(plain_password: str, key_id: str = None) -> str:
    """
    Criptografar senha usando Fernet.
    
    Args:
        plain_password: Senha em texto plano
        key_id: Identificador da chave (padrão: DEFAULT_KEY_ID)
    
    Returns:
        str: Senha criptografada (token Fernet base64)
    """
    key_id = key_id or DEFAULT_KEY_ID
    
    try:
        key = _get_master_key(key_id)
        f = Fernet(key)
        
        # Criptografar
        token = f.encrypt(plain_password.encode()).decode()
        
        logger.debug(f"Senha criptografada com sucesso usando chave '{key_id}'")
        return token
    
    except Exception as e:
        logger.error(f"Erro ao criptografar senha: {str(e)}")
        raise


def decrypt_password(encrypted_password: str, crypto_scheme: str = None, key_id: str = None) -> str:
    """
    Descriptografar senha usando Fernet.
    
    Args:
        encrypted_password: Senha criptografada (token Fernet)
        crypto_scheme: Esquema de criptografia (para validação)
        key_id: Identificador da chave (padrão: DEFAULT_KEY_ID)
    
    Returns:
        str: Senha descriptografada em texto plano
        
    Raises:
        ValueError: Se token inválido ou esquema não suportado
        RuntimeError: Se chave não for encontrada
    """
    key_id = key_id or DEFAULT_KEY_ID
    crypto_scheme = crypto_scheme or DEFAULT_SCHEME
    
    # Validar esquema
    if crypto_scheme != DEFAULT_SCHEME:
        logger.error(f"Esquema de criptografia não suportado: {crypto_scheme}")
        raise ValueError(f"Esquema de criptografia não suportado: {crypto_scheme}")
    
    try:
        key = _get_master_key(key_id)
        f = Fernet(key)
        
        # Descriptografar
        plain_password = f.decrypt(encrypted_password.encode()).decode()
        
        logger.debug(f"Senha descriptografada com sucesso usando chave '{key_id}'")
        return plain_password
    
    except InvalidToken:
        logger.error("Token inválido - falha na descriptografia")
        raise ValueError("Falha na descriptografia - token inválido ou corrompido")
    
    except Exception as e:
        logger.error(f"Erro ao descriptografar senha: {str(e)}")
        raise


def rotate_encryption_key(old_key_id: str, new_key_id: str = None) -> bytes:
    """
    Rotacionar chave de criptografia (para migração de dados).
    
    Gera nova chave e retorna a chave antiga para permitir descriptografia.
    
    Args:
        old_key_id: ID da chave antiga
        new_key_id: ID da nova chave (padrão: old_key_id + "_v2")
    
    Returns:
        bytes: Chave nova gerada
    """
    new_key_id = new_key_id or f"{old_key_id}_v2"
    
    try:
        # Recuperar chave antiga (para validação)
        old_key = _get_master_key(old_key_id)
        logger.info(f"Iniciando rotação: {old_key_id} -> {new_key_id}")
        
        # Gerar e armazenar nova chave
        new_key = generate_and_store_master_key(new_key_id, force=True)
        
        logger.warning(
            f"Chave rotacionada com sucesso. "
            f"Rededique dados de '{old_key_id}' para '{new_key_id}'"
        )
        
        return new_key
    
    except Exception as e:
        logger.error(f"Erro durante rotação de chave: {str(e)}")
        raise


def get_encryption_info() -> Dict[str, str]:
    """
    Obter informações sobre o sistema de criptografia.
    
    Returns:
        Dict com informações de configuração e status
    """
    return {
        "default_scheme": get_default_scheme(),
        "default_key_id": get_default_key_id(),
        "keyring_available": KEYRING_AVAILABLE,
        "env_key_present": bool(_get_master_key_from_env(DEFAULT_KEY_ID)),
        "service_name": SERVICE_NAME,
    }


# Função de suporte para inicializar o sistema de criptografia
def initialize_encryption_system():
    """Inicializar sistema de criptografia gerando chave mestra se não existir."""
    try:
        generate_and_store_master_key()
        logger.info("Sistema de criptografia inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de criptografia: {str(e)}")
        # Não falhar completamente, apenas logar
