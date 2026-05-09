import subprocess
from unittest.mock import patch, MagicMock
import pytest
from shorts.providers.llm.cli_subprocess import run_cli_command, SAFE_ENV_KEYS
from shorts.providers.llm.base import ProviderError

def test_run_cli_command_success():
    """Test successful CLI command execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "hello world"
    mock_result.stderr = ""
    
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        output = run_cli_command(["echo", "hello"], input_text="input")
        
        assert output == "hello world"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["echo", "hello"]
        assert kwargs["input"] == "input"
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

def test_run_cli_command_failure():
    """Test CLI command failure with non-zero exit code."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "error message"
    
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ProviderError) as excinfo:
            run_cli_command(["false"])
        assert "exit code 1" in str(excinfo.value)
        assert "error message" in str(excinfo.value)

def test_run_cli_command_timeout():
    """Test CLI command timeout."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["echo"], timeout=1.0)):
        with pytest.raises(ProviderError) as excinfo:
            run_cli_command(["echo"], timeout=1.0)
        assert "timed out after 1.0s" in str(excinfo.value)

def test_run_cli_command_env_filtering():
    """Test environment variable filtering."""
    with patch("os.environ", {"PATH": "/usr/bin", "SECRET": "hidden", "HOME": "/home/user"}):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_cli_command(["echo"])
            
            _, kwargs = mock_run.call_args
            env = kwargs["env"]
            assert "PATH" in env
            assert "HOME" in env
            assert "SECRET" not in env
            # Verify it only contains keys from SAFE_ENV_KEYS or env_allowlist
            for k in env:
                assert k in SAFE_ENV_KEYS

def test_run_cli_command_env_allowlist():
    """Test environment variable allowlist."""
    with patch("os.environ", {"PATH": "/usr/bin", "CUSTOM": "value"}):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_cli_command(["echo"], env_allowlist=["CUSTOM"])
            
            _, kwargs = mock_run.call_args
            env = kwargs["env"]
            assert "PATH" in env
            assert "CUSTOM" in env
            assert env["CUSTOM"] == "value"
