import os
import sqlite3
import pytest

from shorts.nodes.thumbnail import run


def test_thumbnail_placeholder_video(memory_db, tmp_path):
    job_id = "job_thumb_001"

    video_dir = tmp_path / "data" / "video"
    video_dir.mkdir(parents=True)
    # Simulate a placeholder: render node would write text to a .mp4 path,
    # but we register it in step_results with .txt suffix to trigger thumbnail's
    # placeholder detection (as per node spec).
    video_file = video_dir / f"{job_id}_render.txt"
    video_file.write_text("placeholder render content")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "render", "done", str(video_file)),
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path.endswith("_thumb.jpg")
    assert os.path.exists(result.output_path)
    assert result.output_checksum is not None


def test_thumbnail_missing_render(memory_db, tmp_path):
    job_id = "job_thumb_002"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
    assert "render" in result.error_msg
