import pytest
try:
    from shorts.providers.llm import get_llm_provider
except ImportError:
    get_llm_provider = None

def test_get_llm_provider_invalid():
    """get_llm_provider should raise ValueError for invalid provider name."""
    assert get_llm_provider is not None, "get_llm_provider not imported"
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("invalid")
