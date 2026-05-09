import pytest
from unittest.mock import Mock, patch
from shorts.providers.clips.pexels import PexelsClipsProvider
from shorts.providers.clips.base import ProviderError

@pytest.fixture
def provider():
    with patch.dict("os.environ", {"PEXELS_API_KEY": "test_key"}):
        return PexelsClipsProvider()

@patch("requests.get")
def test_pexels_search_success(mock_get, provider):
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 123,
                "duration": 10,
                "video_files": [
                    {"link": "https://pexels.com/video1.mp4", "width": 1080, "height": 1920}
                ],
                "image": "https://pexels.com/thumb1.jpg"
            }
        ]
    }
    mock_get.return_value = mock_response

    results = provider.search("ocean", count=1)

    assert len(results) == 1
    assert results[0]["id"] == "123"
    assert results[0]["url"] == "https://pexels.com/video1.mp4"
    assert results[0]["duration"] == 10.0
    
    # Verify orientation=portrait was passed
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["orientation"] == "portrait"
    assert kwargs["headers"]["Authorization"] == "test_key"

@patch("requests.get")
def test_pexels_search_error(mock_get, provider):
    mock_response = Mock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    with pytest.raises(ProviderError):
        provider.search("ocean")
