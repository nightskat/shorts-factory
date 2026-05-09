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

@pytest.mark.parametrize("provider", ["codex-cli"])
def test_get_llm_provider_placeholders(provider):
    """get_llm_provider should raise NotImplementedError for valid placeholders."""
    with pytest.raises(NotImplementedError, match=f"Provider {provider} not yet implemented"):
        get_llm_provider(provider)

def test_get_llm_provider_openrouter(monkeypatch):
    """get_llm_provider should return OpenRouterLLMProvider."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = get_llm_provider("openrouter")
    assert provider.provider_id == "openrouter"
    assert provider.name() == "OpenRouter"

def test_get_llm_provider_claude_cli():
    """get_llm_provider should return ClaudeCLILLMProvider."""
    from unittest.mock import patch
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = "claude version 1.2.3"
        provider = get_llm_provider("claude-cli")
        assert provider.provider_id == "claude-cli"
        assert "Claude CLI" in provider.name()
