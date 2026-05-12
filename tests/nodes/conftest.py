import pytest
from typing import Any, Dict
from unittest.mock import MagicMock


@pytest.fixture
def media_dir(tmp_path):
    """Fixture providing a temporary empty directory for media files."""
    media = tmp_path / "media"
    media.mkdir()
    return str(media)


@pytest.fixture
def fake_execution_context() -> Dict[str, Any]:
    """Fixture providing a fake execution context snapshot."""
    return {
        "job_id": "test_job_123",
        "topic": "test topic",
        "script": "This is a test script.",
        "voice_id": "test_voice",
        "status": "pending",
        "metadata": {},
    }


@pytest.fixture
def mock_llm_factory():
    """Fixture providing a mocked LLM factory."""
    mock_factory = MagicMock()
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Mocked LLM response"
    mock_factory.get_provider.return_value = mock_provider
    return mock_factory


import sqlite3
from shorts.db import SCHEMA


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    yield conn
    conn.close()
