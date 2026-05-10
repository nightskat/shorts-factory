import json
import re
from typing import Optional
from shorts.providers.llm.base import LLMProvider, ProviderError
from shorts.providers.llm.cli_subprocess import run_cli_command


class GeminiCLILLMProvider(LLMProvider):
    """
    LLM Provider using the Gemini CLI.
    """

    def __init__(self, env: dict = None):
        self._env = env or {}
        self._version: Optional[str] = None
        self._probe_version()

    def _probe_version(self):
        """Run 'gemini --version' and cache the result."""
        try:
            output = run_cli_command(["gemini", "--version"], timeout=5.0)
            match = re.search(r"([\d.]+)", output)
            if match:
                self._version = match.group(1)
            else:
                self._version = output.strip()[:20]
        except ProviderError:
            self._version = "unknown"

    @property
    def provider_id(self) -> str:
        return "gemini-cli"

    @property
    def contract_version(self) -> str:
        return "v1"

    def name(self) -> str:
        return f"Gemini CLI (experimental / user-risk, v{self._version})"

    def complete(self, system: str, user: str, **kwargs) -> str:
        """
        Execute Gemini CLI completion via prompt argument and json output.
        """
        prompt = f"{system}\n\n{user}"
        cmd = ["gemini", "-p", prompt, "--output-format", "json"]

        try:
            stdout = run_cli_command(cmd)

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as e:
                snippet = stdout[:100] + ("..." if len(stdout) > 100 else "")
                raise ProviderError(
                    f"Failed to parse JSON response from Gemini CLI: {str(e)}\n"
                    f"Output snippet: {snippet}"
                )

            if "response" not in data:
                raise ProviderError(
                    f"Missing 'response' field in Gemini CLI JSON output. "
                    f"Received: {stdout[:200]}"
                )

            return data["response"]

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Unexpected error during Gemini CLI execution: {str(e)}")
