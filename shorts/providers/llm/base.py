from abc import ABC, abstractmethod

class ProviderError(Exception):
    """Base class for all provider-related errors."""
    pass

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

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
    def complete(self, system: str, user: str, **kwargs) -> str:
        """Generate a completion from the LLM."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        pass
