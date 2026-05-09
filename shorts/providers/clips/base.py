from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ProviderError(Exception):
    """Base class for all provider-related errors."""
    pass

class ClipsProvider(ABC):
    """Abstract base class for all clip providers."""

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
    def search(self, query: str, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for clips.
        Returns a list of normalized clips:
        [{"id": str, "url": str, "duration": float, "thumbnail": str, ...}]
        """
        pass
