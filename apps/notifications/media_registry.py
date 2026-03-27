"""Registry de tipos de mídia suportados pelo WhatsApp."""

from typing import Dict, Set, Optional


class MediaTypeConfig:
    """Configuração de um tipo de mídia suportado."""

    def __init__(
        self,
        payload_key: str,
        supports_caption: bool = False,
        supports_voice: bool = False,
        supports_filename: bool = False,
        default_extension: str = "bin",
    ):
        """
        Args:
            payload_key: Chave do bloco no payload webhook (ex: 'image', 'video', 'audio', 'document')
            supports_caption: Se o tipo suporta campo caption
            supports_voice: Se o tipo suporta flag voice (específico para audio)
            supports_filename: Se o tipo suporta campo filename (específico para document)
            default_extension: Extensão padrão se não conseguir derivar de mime_type
        """
        self.payload_key = payload_key
        self.supports_caption = supports_caption
        self.supports_voice = supports_voice
        self.supports_filename = supports_filename
        self.default_extension = default_extension

    def __repr__(self):
        return f"MediaTypeConfig(key={self.payload_key}, caption={self.supports_caption}, voice={self.supports_voice}, filename={self.supports_filename})"


class MediaTypeRegistry:
    """Registry centralizado de tipos de mídia suportados."""

    _TYPES: Dict[str, MediaTypeConfig] = {
        "image": MediaTypeConfig(
            payload_key="image",
            supports_caption=True,
            default_extension="jpg",
        ),
        "video": MediaTypeConfig(
            payload_key="video",
            supports_caption=True,
            default_extension="mp4",
        ),
        "document": MediaTypeConfig(
            payload_key="document",
            supports_caption=True,
            supports_filename=True,
            default_extension="pdf",
        ),
        "audio": MediaTypeConfig(
            payload_key="audio",
            supports_caption=False,
            supports_voice=True,
            default_extension="ogg",
        ),
    }

    @classmethod
    def get(cls, media_type: str) -> Optional[MediaTypeConfig]:
        """
        Retorna a configuração de um tipo de mídia.

        Args:
            media_type: Tipo de mídia (ex: 'image', 'video', 'audio', 'document')

        Returns:
            MediaTypeConfig ou None se tipo não registrado
        """
        return cls._TYPES.get(str(media_type).lower())

    @classmethod
    def is_supported(cls, media_type: str) -> bool:
        """Verifica se um tipo de mídia é suportado."""
        return cls.get(media_type) is not None

    @classmethod
    def get_supported_types(cls) -> Set[str]:
        """Retorna conjunto de todos os tipos suportados."""
        return set(cls._TYPES.keys())

    @classmethod
    def get_payload_key(cls, media_type: str) -> Optional[str]:
        """Retorna a chave do bloco no payload para um tipo de mídia."""
        config = cls.get(media_type)
        return config.payload_key if config else None

    @classmethod
    def supports_caption(cls, media_type: str) -> bool:
        """Verifica se um tipo de mídia suporta caption."""
        config = cls.get(media_type)
        return config.supports_caption if config else False

    @classmethod
    def supports_voice(cls, media_type: str) -> bool:
        """Verifica se um tipo de mídia suporta flag voice."""
        config = cls.get(media_type)
        return config.supports_voice if config else False

    @classmethod
    def supports_filename(cls, media_type: str) -> bool:
        """Verifica se um tipo de mídia suporta campo filename."""
        config = cls.get(media_type)
        return config.supports_filename if config else False

    @classmethod
    def get_default_extension(cls, media_type: str) -> str:
        """Retorna extensão padrão para um tipo de mídia."""
        config = cls.get(media_type)
        return config.default_extension if config else "bin"
