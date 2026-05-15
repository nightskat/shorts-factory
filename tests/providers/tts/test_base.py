from abc import ABC
try:
    from shorts.providers.tts import TTSProvider
except ImportError:
    TTSProvider = None

def test_tts_provider_abc():
    """TTSProvider should be an abstract base class."""
    assert TTSProvider is not None, "TTSProvider not imported"
    assert issubclass(TTSProvider, ABC)
