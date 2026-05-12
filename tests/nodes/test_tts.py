import os
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from shorts.nodes.tts import run


@patch("shorts.nodes.tts.get_tts_provider")
def test_tts_node_success(mock_get_provider, memory_db, tmp_path):
    # Setup the mock provider
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider

    job_id = "test_job_123"
    
    # Create a fake script file
    script_content = "Hello, world!"
    script_path = tmp_path / f"{job_id}_script.txt"
    script_path.write_text(script_content)

    # Insert fake idea_gen step output
    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "idea_gen", "done", str(script_path))
    )
    memory_db.commit()

    # Mock synthesize to just create a dummy file
    def mock_synthesize(text, output_path, **kwargs):
        with open(output_path, "wb") as f:
            f.write(b"fake audio data")
        return output_path
    
    mock_provider.synthesize.side_effect = mock_synthesize

    execution_context = {
        "env": {
            "TTS_PROVIDER": "test-provider",
            "TTS_VOICE": "test-voice",
            "TTS_RATE": "+10%"
        },
        "workspace_dir": str(tmp_path)
    }

    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path == os.path.join(tmp_path, "data", "audio", f"{job_id}_tts.mp3")
    assert os.path.exists(result.output_path)
    assert result.output_checksum is not None
    
    # Check if provider was called with correct arguments
    mock_provider.synthesize.assert_called_once_with(
        text=script_content,
        output_path=result.output_path + ".tmp",
        voice="test-voice",
        rate="+10%"
    )

def test_tts_node_missing_idea_gen(memory_db, tmp_path):
    job_id = "test_job_456"
    execution_context = {
        "env": {},
        "workspace_dir": str(tmp_path)
    }

    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "error"
    assert "Could not find successful idea_gen step output" in result.error_msg
