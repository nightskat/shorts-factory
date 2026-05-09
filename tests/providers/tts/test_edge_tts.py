import sys
from unittest.mock import MagicMock, AsyncMock

# Mock edge_tts module before it's imported by EdgeTTSProvider
mock_edge_tts = MagicMock()
mock_edge_tts.Communicate = MagicMock()
mock_edge_tts.list_voices = AsyncMock() # Default to async
sys.modules["edge_tts"] = mock_edge_tts

import pytest
import asyncio
from shorts.providers.tts.edge_tts import EdgeTTSProvider
from shorts.providers.tts.base import ProviderError

def test_edge_tts_metadata():
    provider = EdgeTTSProvider()
    assert provider.provider_id == "edge-tts"
    assert provider.contract_version == "1.0.0"
    assert "Edge-TTS" in provider.name()

def test_edge_tts_synthesize_success():
    # Mock the async save method
    mock_instance = MagicMock()
    mock_instance.save = AsyncMock()
    mock_edge_tts.Communicate.return_value = mock_instance
    
    provider = EdgeTTSProvider()
    path = provider.synthesize(
        "Hello world", 
        "test.mp3", 
        voice="en-US-GuyNeural",
        rate="+10%",
        pitch="+0Hz"
    )
    
    assert path == "test.mp3"
    mock_edge_tts.Communicate.assert_called_once_with(
        "Hello world",
        voice="en-US-GuyNeural",
        rate="+10%",
        pitch="+0Hz"
    )
    mock_instance.save.assert_called_once_with("test.mp3")

def test_edge_tts_synthesize_error():
    mock_instance = MagicMock()
    mock_instance.save = AsyncMock(side_effect=Exception("TTS failed"))
    mock_edge_tts.Communicate.return_value = mock_instance
    
    provider = EdgeTTSProvider()
    with pytest.raises(ProviderError) as excinfo:
        provider.synthesize("Hello", "error.mp3")
    
    assert "TTS failed" in str(excinfo.value)

def test_edge_tts_list_voices_success():
    # Mock list_voices to return a coroutine that resolves to a list
    mock_edge_tts.list_voices.return_value = [
        {"Name": "Microsoft Server Speech Text to Speech Voice (en-US, GuyNeural)", "ShortName": "en-US-GuyNeural", "Gender": "Male"}
    ]
    
    provider = EdgeTTSProvider()
    voices = provider.list_voices()
    
    assert len(voices) == 1
    assert voices[0]["id"] == "en-US-GuyNeural"
    assert voices[0]["gender"] == "Male"

def test_edge_tts_list_voices_error():
    mock_edge_tts.list_voices.side_effect = Exception("List failed")
    
    provider = EdgeTTSProvider()
    with pytest.raises(ProviderError):
        provider.list_voices()
