# factory.py — LLM provider factory
# Returns the correct provider instance given a name string and env dict.
from shorts.providers.llm.base import LLMProvider
from shorts.providers.llm.openrouter import OpenRouterLLMProvider
from shorts.providers.llm.claude_cli import ClaudeCLILLMProvider
from shorts.providers.llm.codex_cli import CodexCLILLMProvider
from shorts.providers.llm.gemini_cli import GeminiCLILLMProvider


def get_llm_provider(provider_name: str, env: dict = None) -> LLMProvider:
    if env is None:
        env = {}

    if provider_name == "openrouter":
        return OpenRouterLLMProvider(env=env)

    if provider_name == "claude-cli":
        return ClaudeCLILLMProvider(env=env)

    if provider_name == "codex-cli":
        return CodexCLILLMProvider(env=env)

    if provider_name == "gemini-cli":
        return GeminiCLILLMProvider(env=env)

    raise ValueError(f"Unknown LLM provider: {provider_name}")
