import pytest
from abc import ABC
try:
    from shorts.providers.clips import ClipsProvider
except ImportError:
    ClipsProvider = None

def test_clips_provider_abc():
    """ClipsProvider should be an abstract base class."""
    assert ClipsProvider is not None, "ClipsProvider not imported"
    assert issubclass(ClipsProvider, ABC)
