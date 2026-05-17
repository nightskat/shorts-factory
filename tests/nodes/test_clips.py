import json
import os

from shorts.nodes.clips import run






def test_clips_no_pexels_creates_placeholders(memory_db, tmp_path):
    job_id = "job_clips_001"

    scenes = [
        {"description": "A cat on a mat", "duration_seconds": 5},
        {"description": "A dog in a park", "duration_seconds": 4},
    ]
    scenes_file = tmp_path / f"{job_id}_scenes.json"
    scenes_file.write_text(json.dumps(scenes))

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "scenes", "done", str(scenes_file))
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path.endswith("_clips.json")
    assert result.output_checksum is not None

    with open(result.output_path, "r") as f:
        manifest = json.load(f)

    assert len(manifest) == 2
    for i, item in enumerate(manifest):
        assert item["clip_path"].endswith(".txt")
        assert os.path.exists(item["clip_path"])
        assert item["duration_seconds"] == scenes[i]["duration_seconds"]


def test_clips_missing_scenes(memory_db, tmp_path):
    job_id = "job_clips_002"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
    assert "scenes" in result.error_msg

def test_clips_pexels_ssrf_protection(memory_db, tmp_path):
    import pytest
    from unittest.mock import MagicMock
    from shorts.nodes.clips import _process_scene

    pexels_mock = MagicMock()
    pexels_mock.search.return_value = [{"url": "file:///etc/passwd"}]

    with pytest.raises(ValueError, match="Invalid URL scheme in Pexels result: file:///etc/passwd"):
        _process_scene(
            i=0,
            scene={"description": "Test", "duration_seconds": 5},
            job_id="test_ssrf",
            clips_dir=str(tmp_path),
            pexels=pexels_mock
        )
