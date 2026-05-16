import sqlite3
import pytest

from shorts.nodes.upload_yt import run







def test_upload_yt_first_run_simulated(memory_db, tmp_path):
    job_id = "job_upload_001"

    render_file = tmp_path / f"{job_id}_render.mp4"
    render_file.write_bytes(b"fake video")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "render", "done", str(render_file))
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert "youtube.com/watch?v=" in result.output_path
    assert "SIMULATED_" in result.output_path

    # Verify DB was updated
    row = memory_db.execute(
        "SELECT status, video_id FROM youtube_uploads WHERE job_id = ?", (job_id,)
    ).fetchone()
    assert row[0] == "completed"
    assert row[1].startswith("SIMULATED_")


def test_upload_yt_idempotent_rerun(memory_db, tmp_path):
    job_id = "job_upload_002"

    render_file = tmp_path / f"{job_id}_render.mp4"
    render_file.write_bytes(b"fake video")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "render", "done", str(render_file))
    )
    # Pre-seed a completed upload record
    memory_db.execute(
        "INSERT INTO youtube_uploads (job_id, idempotency_key, status, video_id) VALUES (?, ?, ?, ?)",
        (job_id, "abc123", "completed", "EXISTING_VIDEO_ID")
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert "EXISTING_VIDEO_ID" in result.output_path


def test_upload_yt_with_real_uploader(memory_db, tmp_path):
    job_id = "job_upload_003"

    render_file = tmp_path / f"{job_id}_render.mp4"
    render_file.write_bytes(b"fake video")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "render", "done", str(render_file))
    )
    memory_db.commit()

    class FakeUploader:
        def upload(self, video_path, title, description):
            return "REAL_VIDEO_XYZ"

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {"youtube_uploader": FakeUploader()})

    assert result.status == "done"
    assert "REAL_VIDEO_XYZ" in result.output_path


def test_upload_yt_missing_render(memory_db, tmp_path):
    job_id = "job_upload_004"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
    assert "render" in result.error_msg
