import json
import pytest
from unittest.mock import patch
from shorts.providers.llm.claude_cli import ClaudeCLILLMProvider
from shorts.providers.llm.base import ProviderError

@pytest.fixture
def provider():
    # Patch run_cli_command for version probe in __init__
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = "claude version 0.1.0"
        return ClaudeCLILLMProvider()

def test_provider_properties(provider):
    assert provider.provider_id == "claude-cli"
    assert provider.contract_version == "v1"
    assert "local-only" in provider.name().lower()

def test_version_probe():
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = "claude version 0.1.0"
        p = ClaudeCLILLMProvider()
        assert p._version == "0.1.0"
        mock_run.assert_called_with(["claude", "--version"], timeout=5.0)

def test_complete_success(provider):
    system = "You are a helpful assistant."
    user = "Hello!"
    expected_response = "Hi there!"
    
    mock_stdout = json.dumps({"content": expected_response})
    
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = mock_stdout
        
        response = provider.complete(system, user)
        
        assert response == expected_response
        
        # Verify call arguments
        args, kwargs = mock_run.call_args
        assert args[0] == ["claude", "-p", "--output-format", "json", "--input-format", "stream-json"]
        
        # Verify input JSON
        input_json = json.loads(kwargs["input_text"])
        assert input_json["messages"][0]["role"] == "system"
        assert input_json["messages"][0]["content"] == system
        assert input_json["messages"][1]["role"] == "user"
        assert input_json["messages"][1]["content"] == user

def test_complete_invalid_json(provider):
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = "not json"
        
        with pytest.raises(ProviderError) as excinfo:
            provider.complete("sys", "user")
        assert "Failed to parse JSON response" in str(excinfo.value)

def test_complete_missing_content(provider):
    with patch("shorts.providers.llm.claude_cli.run_cli_command") as mock_run:
        mock_run.return_value = json.dumps({"something": "else"})
        
        with pytest.raises(ProviderError) as excinfo:
            provider.complete("sys", "user")
        assert "Missing 'content' in JSON response" in str(excinfo.value)

def test_complete_cli_error(provider):
    with patch("shorts.providers.llm.claude_cli.run_cli_command", side_effect=ProviderError("CLI failed")):
        with pytest.raises(ProviderError) as excinfo:
            provider.complete("sys", "user")
        assert "CLI failed" in str(excinfo.value)
