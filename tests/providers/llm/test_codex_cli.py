import json
import pytest
from unittest.mock import patch, MagicMock
from shorts.providers.llm.codex_cli import CodexCLILLMProvider
from shorts.providers.llm.base import ProviderError

@pytest.fixture
def mock_run_cli():
    with patch("shorts.providers.llm.codex_cli.run_cli_command") as mock:
        yield mock

def test_codex_cli_init_version_probe(mock_run_cli):
    mock_run_cli.return_value = "codex-cli 0.130.0\n"
    provider = CodexCLILLMProvider()
    assert provider._version == "0.130.0"
    mock_run_cli.assert_any_call(["codex", "--version"], timeout=5.0)

def test_codex_cli_name(mock_run_cli):
    mock_run_cli.return_value = "codex-cli 0.130.0\n"
    provider = CodexCLILLMProvider()
    assert "experimental / user-risk" in provider.name()
    assert "0.130.0" in provider.name()

def test_codex_cli_complete_success(mock_run_cli):
    mock_run_cli.side_effect = [
        "codex-cli 0.130.0\n",  # version probe
        '{"type":"item.completed","item":{"type":"agent_message","text":"Final response."}}\n' # completion
    ]
    provider = CodexCLILLMProvider()
    
    response = provider.complete("System prompt", "User prompt")
    
    assert response == "Final response."
    # Check that it uses stdin for prompt as mandated
    mock_run_cli.assert_called_with(
        ["codex", "exec", "--json", "-"],
        input_text="System prompt\n\nUser prompt"
    )

def test_codex_cli_complete_json_error(mock_run_cli):
    mock_run_cli.side_effect = [
        "codex-cli 0.130.0\n",
        "invalid json"
    ]
    provider = CodexCLILLMProvider()
    
    with pytest.raises(ProviderError, match="Failed to parse JSONL"):
        provider.complete("System", "User")

def test_codex_cli_complete_missing_content(mock_run_cli):
    mock_run_cli.side_effect = [
        "codex-cli 0.130.0\n",
        '{"type":"other"}\n'
    ]
    provider = CodexCLILLMProvider()
    
    with pytest.raises(ProviderError, match="No agent message found"):
        provider.complete("System", "User")
