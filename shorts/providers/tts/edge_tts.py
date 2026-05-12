import asyncio
import edge_tts
from typing import List, Dict, Any
from shorts.providers.tts.base import TTSProvider, ProviderError

class EdgeTTSProvider(TTSProvider):
    """
    Edge-TTS provider using the undocumented Microsoft Edge TTS API.
    Provides high-quality neural voices for free.
    """

    @property
    def provider_id(self) -> str:
        return "edge-tts"

    @property
    def contract_version(self) -> str:
        return "1.0.0"

    def name(self) -> str:
        return "Edge-TTS (Free)"

    def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """
        Synthesize text to audio using edge-tts.
        
        Args:
            text: Text to synthesize.
            output_path: Path to save the audio file.
            **kwargs: Additional parameters:
                voice: Voice name (default: en-US-GuyNeural)
                rate: Speed (e.g., "+0%", "+10%")
                pitch: Pitch (e.g., "+0Hz", "+5Hz")
        """
        voice = kwargs.get("voice", "en-US-GuyNeural")
        rate = kwargs.get("rate", "+0%")
        pitch = kwargs.get("pitch", "+0Hz")

        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
            asyncio.run(communicate.save(output_path))
            return output_path
        except Exception as e:
            raise ProviderError(f"Edge-TTS synthesis failed: {str(e)}") from e

    def list_voices(self) -> List[Dict[str, Any]]:
        """
        List available voices for Edge-TTS.
        """
        try:
            voices_coro = edge_tts.list_voices()
            if asyncio.iscoroutine(voices_coro):
                raw_voices = asyncio.run(voices_coro)
            else:
                raw_voices = voices_coro
            
            formatted_voices = []
            for v in raw_voices:
                formatted_voices.append({
                    "id": v.get("ShortName") or v.get("Name"),
                    "name": v.get("FriendlyName") or v.get("Name"),
                    "gender": v.get("Gender"),
                    "locale": v.get("Locale"),
                    "raw": v
                })
            return formatted_voices
        except Exception as e:
            raise ProviderError(f"Failed to list Edge-TTS voices: {str(e)}") from e
