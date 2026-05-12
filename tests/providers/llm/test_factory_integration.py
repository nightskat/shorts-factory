import pytest
from unittest.mock import patch
from shorts.providers.llm.factory import get_llm_provider
from shorts.providers.llm.base import LLMProvider

@pytest.mark.parametrize("provider_id", ["openrouter", "claude-cli", "codex-cli"])
def test_factory_returns_valid_provider(provider_id):
    # Mock initialization to avoid env var requirements or CLI probing
    with patch("os.environ.get", return_value="fake-key"), \
         patch("shorts.providers.llm.claude_cli.run_cli_command", return_value="version 1.0"), \
         patch("shorts.providers.llm.codex_cli.run_cli_command", return_value="version 1.0"):
        
        provider = get_llm_provider(provider_id)
        assert isinstance(provider, LLMProvider)
        assert provider.provider_id == provider_id
        assert provider.contract_version == "v1"
        assert callable(provider.complete)
