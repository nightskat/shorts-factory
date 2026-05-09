from typing import Dict, Any
from shorts.providers.llm.base import LLMProvider
from shorts.providers.llm.openrouter import OpenRouterLLMProvider
from shorts.providers.llm.claude_cli import ClaudeCLILLMProvider

def get_llm_provider(provider_name: str) -> LLMProvider:
    """Factory function to get an LLM provider instance."""
    providers = {
        "openrouter": OpenRouterLLMProvider,
        "claude-cli": ClaudeCLILLMProvider,
        "codex-cli": None,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    if provider_name == "openrouter":
        return OpenRouterLLMProvider()
    
    if provider_name == "claude-cli":
        return ClaudeCLILLMProvider()
    
    raise NotImplementedError(f"Provider {provider_name} not yet implemented")
