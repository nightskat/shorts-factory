import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from shorts.providers.tts.edge_tts import EdgeTTSProvider
from shorts.providers.tts.base import ProviderError


def test_edge_tts_metadata():
    provider = EdgeTTSProvider()
    assert provider.provider_id == "edge-tts"
    assert provider.contract_version == "1.0.0"
    assert "Edge-TTS" in provider.name()


def test_edge_tts_synthesize_success():
    mock_instance = MagicMock()
    mock_instance.save = AsyncMock()
    mock_communicate = MagicMock(return_value=mock_instance)

    with patch("shorts.providers.tts.edge_tts.edge_tts") as mock_et:
        mock_et.Communicate = mock_communicate
        provider = EdgeTTSProvider()
        path = provider.synthesize(
            "Hello world",
            "test.mp3",
            voice="en-US-GuyNeural",
            rate="+10%",
            pitch="+0Hz",
        )

    assert path == "test.mp3"
    mock_communicate.assert_called_once_with(
        "Hello world",
        voice="en-US-GuyNeural",
        rate="+10%",
        pitch="+0Hz",
    )
    mock_instance.save.assert_called_once_with("test.mp3")


def test_edge_tts_synthesize_error():
    mock_instance = MagicMock()
    mock_instance.save = AsyncMock(side_effect=Exception("TTS failed"))
    mock_communicate = MagicMock(return_value=mock_instance)

    with patch("shorts.providers.tts.edge_tts.edge_tts") as mock_et:
        mock_et.Communicate = mock_communicate
        provider = EdgeTTSProvider()
        with pytest.raises(ProviderError) as excinfo:
            provider.synthesize("Hello", "error.mp3")

    assert "TTS failed" in str(excinfo.value)


def test_edge_tts_list_voices_success():
    fake_voices = [
        {
            "Name": "Microsoft Server Speech Text to Speech Voice (en-US, GuyNeural)",
            "ShortName": "en-US-GuyNeural",
            "Gender": "Male",
            "Locale": "en-US",
            "FriendlyName": "Microsoft Guy Online (Natural)",
        }
    ]

    with patch("shorts.providers.tts.edge_tts.edge_tts") as mock_et:
        mock_et.list_voices.return_value = fake_voices
        provider = EdgeTTSProvider()
        voices = provider.list_voices()

    assert len(voices) == 1
    assert voices[0]["id"] == "en-US-GuyNeural"
    assert voices[0]["gender"] == "Male"


def test_edge_tts_list_voices_error():
    with patch("shorts.providers.tts.edge_tts.edge_tts") as mock_et:
        mock_et.list_voices.side_effect = Exception("List failed")
        provider = EdgeTTSProvider()
        with pytest.raises(ProviderError):
            provider.list_voices()

def test_edge_tts_list_voices_async_error():
    async def fake_voices_coro():
        # Yield invalid data that raises an exception when trying to access .get()
        return ["invalid string data instead of dict"]

    with patch("shorts.providers.tts.edge_tts.edge_tts") as mock_et:
        mock_et.list_voices.return_value = fake_voices_coro()
        provider = EdgeTTSProvider()
        with pytest.raises(ProviderError) as excinfo:
            provider.list_voices()

    assert "Failed to list Edge-TTS voices" in str(excinfo.value)
