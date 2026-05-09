from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ProviderError(Exception):
    """Base class for all provider-related errors."""
    pass

class TTSProvider(ABC):
    """Abstract base class for all TTS providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for the provider."""
        pass

    @property
    @abstractmethod
    def contract_version(self) -> str:
        """Version of the provider contract."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        pass

    @abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """
        Synthesize text to audio.
        Returns the path to the generated audio file.
        """
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices for this provider."""
        pass
