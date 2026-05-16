import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from shorts.nodes.scenes import run






def test_scenes_success(memory_db, tmp_path):
    job_id = "job_scenes_001"

    script_file = tmp_path / f"{job_id}_script.txt"
    script_file.write_text("This is a short script about cats.")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "idea_gen", "done", str(script_file))
    )
    memory_db.commit()

    fake_scenes = [
        {"description": "Cat on couch", "duration_seconds": 5},
        {"description": "Cat plays", "duration_seconds": 4},
    ]
    mock_llm = MagicMock()
    mock_llm.generate.return_value = json.dumps(fake_scenes)

    execution_context = {
        "env": {"LLM_PROVIDER": "mock"},
        "workspace_dir": str(tmp_path),
    }

    with patch("shorts.nodes.scenes.get_llm_provider", return_value=mock_llm):
        result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path.endswith("_scenes.json")
    assert result.output_checksum is not None

    with open(result.output_path, "r") as f:
        loaded = json.load(f)
    assert loaded == fake_scenes


def test_scenes_invalid_json_from_llm(memory_db, tmp_path):
    job_id = "job_scenes_002"

    script_file = tmp_path / f"{job_id}_script.txt"
    script_file.write_text("Another script.")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "idea_gen", "done", str(script_file))
    )
    memory_db.commit()

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "This is not JSON at all."

    execution_context = {
        "env": {"LLM_PROVIDER": "mock"},
        "workspace_dir": str(tmp_path),
    }

    with patch("shorts.nodes.scenes.get_llm_provider", return_value=mock_llm):
        result = run(job_id, execution_context, memory_db, {})

    assert result.status == "error"
    assert "invalid JSON" in result.error_msg.lower() or "json" in result.error_msg.lower()


def test_scenes_missing_idea_gen(memory_db, tmp_path):
    job_id = "job_scenes_003"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
    assert "idea_gen" in result.error_msg
