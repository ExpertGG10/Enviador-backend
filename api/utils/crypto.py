"""
Módulo de criptografia para senhas de email.
Adaptado de Enviador_de_Email/utils/fernet_crypto.py para ambiente Django.
Usa variável de ambiente ENCRYPTION_KEY em vez de keyring.
"""
import os
from cryptography.fernet import Fernet, InvalidToken


def get_encryption_key() -> bytes:
    """
    Get the Fernet encryption key from environment variable.
    
    Returns:
        bytes: The encryption key
    """
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY not configured. "
            "Set the ENCRYPTION_KEY environment variable with a valid Fernet key."
        )
    return key.encode()


def encrypt_password(plain: str) -> str:
    """
    Encrypt a plain password using Fernet.

    Args:
        plain (str): The plain password to encrypt.
        
    Returns:
        str: The encrypted password (Fernet token).
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        token = f.encrypt(plain.encode()).decode()
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to encrypt password: {e}")


def decrypt_password(ciphertext: str) -> str:
    """
    Decrypt an encrypted password using Fernet.

    Args:
        ciphertext (str): The encrypted password (Fernet token).
        
    Returns:
        str: The decrypted plain password.
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise RuntimeError("Invalid encryption token or corrupted data")
    except Exception as e:
        raise RuntimeError(f"Failed to decrypt password: {e}")
