from abc import ABC
try:
    from shorts.providers.llm import LLMProvider
except ImportError:
    LLMProvider = None

def test_llm_provider_abc():
    """LLMProvider should be an abstract base class."""
    assert LLMProvider is not None, "LLMProvider not imported"
    assert issubclass(LLMProvider, ABC)
