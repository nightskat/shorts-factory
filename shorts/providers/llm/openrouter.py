# openrouter.py — OpenRouter HTTP LLM provider
# Calls https://openrouter.ai/api/v1/chat/completions with requests.
import requests
from shorts.providers.llm.base import LLMProvider, ProviderError


class OpenRouterLLMProvider(LLMProvider):

    def __init__(self, env: dict = None):
        if env is None:
            env = {}
        self._api_key = env.get("OPENROUTER_API_KEY", "")
        self._model = env.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    @property
    def provider_id(self) -> str:
        return "openrouter"

    @property
    def contract_version(self) -> str:
        return "v1"

    def name(self) -> str:
        return "OpenRouter"

    def complete(self, system: str, user: str, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            raise ProviderError(f"OpenRouter request failed: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(f"Unexpected OpenRouter response shape: {e}")

    def generate(self, system: str, user: str, **kwargs) -> str:
        return self.complete(system, user, **kwargs)
