import os
import requests
from typing import List, Dict, Any
from .base import ClipsProvider, ProviderError

class PexelsClipsProvider(ClipsProvider):
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            raise ProviderError("PEXELS_API_KEY not found in environment")

    @property
    def provider_id(self) -> str:
        return "pexels"

    @property
    def contract_version(self) -> str:
        return "1.0"

    def name(self) -> str:
        return "Pexels"

    def search(self, query: str, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": count,
            "orientation": "portrait"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise ProviderError(f"Pexels API error: {response.status_code}")
            
            data = response.json()
            results = []
            for video in data.get("videos", []):
                # Find best portrait file (highest resolution or just first)
                video_files = video.get("video_files", [])
                if not video_files:
                    continue
                
                # Normalize to common format
                results.append({
                    "id": str(video["id"]),
                    "url": video_files[0]["link"],
                    "duration": float(video["duration"]),
                    "thumbnail": video.get("image"),
                    "provider": self.provider_id
                })
            return results
        except Exception as e:
            if isinstance(e, ProviderError):
                raise e
            raise ProviderError(f"Pexels search failed: {str(e)}")
