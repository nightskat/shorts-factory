import json
import re
from typing import Optional
from shorts.providers.llm.base import LLMProvider, ProviderError
from shorts.providers.llm.cli_subprocess import run_cli_command

class ClaudeCLILLMProvider(LLMProvider):
    """
    LLM Provider using the Anthropic Claude CLI.
    """
    
    def __init__(self, env: dict = None):
        self._env = env or {}
        self._version: Optional[str] = None
        self._probe_version()

    def _probe_version(self):
        """Run 'claude --version' and cache the result."""
        try:
            output = run_cli_command(["claude", "--version"], timeout=5.0)
            # Example output: "claude version 0.1.0" or "version 0.1.0"
            # Anchoring the search to handle multiple version strings if present
            match = re.search(r"(?:claude\s+)?version\s+([\d.]+)", output, re.IGNORECASE)
            if match:
                self._version = match.group(1)
            else:
                self._version = output.strip()[:20]
        except ProviderError:
            # If we can't probe version, we still allow initialization 
            # but set a default.
            self._version = "unknown"

    @property
    def provider_id(self) -> str:
        return "claude-cli"

    @property
    def contract_version(self) -> str:
        return "v1"

    def name(self) -> str:
        return f"Claude CLI (local-only, v{self._version})"

    def complete(self, system: str, user: str, **kwargs) -> str:
        """
        Execute Claude CLI completion via stream-json input and json output.
        """
        cmd = ["claude", "-p", "--output-format", "json", "--input-format", "stream-json"]
        
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
        
        input_text = json.dumps(payload)
        
        try:
            stdout = run_cli_command(cmd, input_text=input_text)
            
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as e:
                # Include first 100 chars of stdout for better debugging
                snippet = stdout[:100] + ("..." if len(stdout) > 100 else "")
                raise ProviderError(f"Failed to parse JSON response from Claude CLI: {str(e)}\nOutput snippet: {snippet}")
            
            if "content" not in data:
                raise ProviderError(f"Missing 'content' in JSON response from Claude CLI. Received: {stdout[:200]}")
                
            return data["content"]
            
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Unexpected error during Claude CLI execution: {str(e)}")
