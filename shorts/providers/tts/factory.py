from typing import Any
from shorts.providers.tts.base import TTSProvider, ProviderError
from shorts.providers.tts.edge_tts import EdgeTTSProvider

def get_tts_provider(provider_id: str, env: dict[str, Any]) -> TTSProvider:
    """
    Factory to get a TTS provider by ID.
    
    Args:
        provider_id: The ID of the provider (e.g., 'edge-tts').
        env: Environment variables/settings.
        
    Returns:
        An instance of a TTSProvider.
        
    Raises:
        ValueError: If the provider is not supported.
    """
    if provider_id == "edge-tts":
        return EdgeTTSProvider()
    
    raise ValueError(f"Unsupported TTS provider: {provider_id}")
