import os
import subprocess
from typing import Dict, List, Optional
from shorts.providers.llm.base import ProviderError

SAFE_ENV_KEYS = {
    "PATH", "HOME", "USERPROFILE", "LANG", "LC_ALL", "TERM", "TMPDIR", "TEMP", "TMP",
    "SYSTEMROOT", "COMSPEC", "PATHEXT", "APPDATA", "LOCALAPPDATA", "NO_COLOR", "CI",
    "CLAUDE_CONFIG_DIR", "CODEX_HOME"
}

def _get_filtered_env(env_allowlist: Optional[List[str]] = None) -> Dict[str, str]:
    """Get a filtered environment dictionary based on allowed keys."""
    allowed_keys = SAFE_ENV_KEYS.copy()
    if env_allowlist:
        allowed_keys.update(env_allowlist)

    return {k: v for k, v in os.environ.items() if k in allowed_keys}

def _handle_subprocess_error(result: subprocess.CompletedProcess) -> None:
    """Handle non-zero exit codes from subprocess execution."""
    if result.returncode != 0:
        error_msg = f"CLI command failed with exit code {result.returncode}\n"
        if result.stderr:
            error_msg += f"Stderr: {result.stderr.strip()}"
        raise ProviderError(error_msg)

def run_cli_command(
    args: List[str],
    input_text: Optional[str] = None,
    timeout: float = 30.0,
    env_allowlist: Optional[List[str]] = None
) -> str:
    """
    Run a CLI command with hardened security settings.
    
    Args:
        args: List of command line arguments (argv).
        input_text: Text to be sent to stdin.
        timeout: Maximum execution time in seconds.
        env_allowlist: Additional environment variables to allow.
        
    Returns:
        The stdout of the command.
        
    Raises:
        ProviderError: If the command fails or times out.
    """
    filtered_env = _get_filtered_env(env_allowlist)
    
    try:
        result = subprocess.run(
            args,
            input=input_text,
            env=filtered_env,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False  # We handle check manually to provide better error messages
        )
        
        _handle_subprocess_error(result)

        return result.stdout
        
    except subprocess.TimeoutExpired as e:
        raise ProviderError(f"CLI command timed out after {timeout}s") from e
    except Exception as e:
        if isinstance(e, ProviderError):
            raise
        raise ProviderError(f"Failed to execute CLI command: {str(e)}") from e
