import os
import requests
from typing import List, Dict, Any
from shorts.providers.clips.base import ClipsProvider, ProviderError

class PexelsClipsProvider(ClipsProvider):
    """
    Clips Provider using the Pexels API.
    """

    def __init__(self):
        self._api_key = os.getenv("PEXELS_API_KEY")
        if not self._api_key:
            raise ProviderError("PEXELS_API_KEY not found in environment.")
        self._base_url = "https://api.pexels.com/videos"

    @property
    def provider_id(self) -> str:
        return "pexels"

    @property
    def contract_version(self) -> str:
        return "v1"

    def name(self) -> str:
        return "Pexels Stock Clips"

    def search(self, query: str, count: int = 5, **kwargs) -> List[Dict[Any, Any]]:
        """
        Search for portrait orientation video clips on Pexels.
        """
        headers = {"Authorization": self._api_key}
        params = {
            "query": query,
            "per_page": count,
            "orientation": "portrait"
        }
        
        # Use a reasonable timeout to prevent hanging
        timeout = kwargs.get("timeout", 30)

        try:
            response = requests.get(
                f"{self._base_url}/search", 
                headers=headers, 
                params=params, 
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise ProviderError(f"Pexels API error: {response.status_code} - {response.text}")

            data = response.json()
            videos = data.get("videos", [])
            results = []

            for video in videos:
                video_files = video.get("video_files", [])
                if not video_files:
                    continue
                
                # Selection logic: prioritize HD and true portrait (width < height)
                # Pexels video_files often have 'width', 'height', 'link', 'quality'
                best_file = self._select_best_file(video_files)
                
                results.append({
                    "id": str(video.get("id", "unknown")),
                    "url": best_file.get("link"),
                    "duration": float(video.get("duration", 0)),
                    "width": best_file.get("width"),
                    "height": best_file.get("height"),
                    "thumbnail": video.get("image"),
                    "provider": self.provider_id
                })

            return results

        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Network error during Pexels search: {str(e)}")
        except Exception as e:
            raise ProviderError(f"Unexpected error in Pexels provider: {str(e)}")

    def _select_best_file(self, video_files: List[Dict]) -> Dict:
        """
        Select the highest quality file that is in portrait mode.
        """
        # 1. Filter for portrait (width < height)
        portraits = [f for f in video_files if f.get("width", 0) < f.get("height", 0)]
        candidates = portraits if portraits else video_files
        
        # 2. Sort by height descending to get highest resolution
        candidates.sort(key=lambda x: x.get("height", 0), reverse=True)
        
        return candidates[0]
