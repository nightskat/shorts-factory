import json
import re
from typing import Optional
from shorts.providers.llm.base import LLMProvider, ProviderError
from shorts.providers.llm.cli_subprocess import run_cli_command

class CodexCLILLMProvider(LLMProvider):
    """
    LLM Provider using the Codex CLI.
    """
    
    def __init__(self, env: dict = None):
        self._env = env or {}
        self._version: Optional[str] = None
        self._probe_version()

    def _probe_version(self):
        """Run 'codex --version' and cache the result."""
        try:
            output = run_cli_command(["codex", "--version"], timeout=5.0)
            # Example output: "codex-cli 0.130.0"
            match = re.search(r"(?:version|cli)\s+([\d.]+)", output, re.IGNORECASE)
            if match:
                self._version = match.group(1)
            else:
                self._version = output.strip()[:20]
        except ProviderError:
            self._version = "unknown"

    @property
    def provider_id(self) -> str:
        return "codex-cli"

    @property
    def contract_version(self) -> str:
        return "v1"

    def name(self) -> str:
        return f"Codex CLI (experimental / user-risk, v{self._version})"

    def complete(self, system: str, user: str, **kwargs) -> str:
        """
        Execute Codex CLI completion via stdin input and jsonl output.
        """
        # Mandate to use STDIN for prompts as per requirement
        cmd = ["codex", "exec", "--json", "-"]
        input_text = f"{system}\n\n{user}"
        
        try:
            stdout = run_cli_command(cmd, input_text=input_text)
            
            if not stdout.strip():
                 raise ProviderError("Empty output from Codex CLI")

            agent_text = None
            lines = stdout.strip().split("\n")
            
            valid_json_found = False
            for line in lines:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    valid_json_found = True
                    # Look for agent message in item.completed event
                    if event.get("type") == "item.completed":
                        item = event.get("item", {})
                        if item.get("type") == "agent_message":
                            agent_text = item.get("text")
                except json.JSONDecodeError:
                    continue
            
            if not valid_json_found:
                raise ProviderError(f"Failed to parse JSONL response from Codex CLI. Output snippet: {stdout[:100]}")

            if agent_text is None:
                raise ProviderError(f"No agent message found in Codex CLI output. Received: {stdout[:200]}")
                
            return agent_text
            
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Unexpected error during Codex CLI execution: {str(e)}")
