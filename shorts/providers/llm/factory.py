from typing import Dict, Any
from shorts.providers.llm.base import LLMProvider

def get_llm_provider(provider_name: str) -> LLMProvider:
    """Factory function to get an LLM provider instance."""
    providers = {
        "openrouter": None,
        "claude-cli": None,
        "codex-cli": None,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    raise NotImplementedError(f"Provider {provider_name} not yet implemented")
