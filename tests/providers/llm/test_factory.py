import pytest
try:
    from shorts.providers.llm import get_llm_provider
except ImportError:
    get_llm_provider = None

def test_get_llm_provider_invalid():
    """get_llm_provider should raise ValueError for invalid provider name."""
    assert get_llm_provider is not None, "get_llm_provider not imported"
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("invalid")

@pytest.mark.parametrize("provider", ["openrouter", "claude-cli", "codex-cli"])
def test_get_llm_provider_placeholders(provider):
    """get_llm_provider should raise NotImplementedError for valid placeholders."""
    with pytest.raises(NotImplementedError, match=f"Provider {provider} not yet implemented"):
        get_llm_provider(provider)
