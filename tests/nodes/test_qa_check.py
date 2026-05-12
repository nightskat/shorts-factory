import os
import sqlite3
import pytest

from shorts.nodes.qa_check import run






def test_qa_check_both_present(memory_db, tmp_path):
    job_id = "job_qa_001"

    render_file = tmp_path / f"{job_id}_render.mp4"
    render_file.write_bytes(b"fake video")
    thumb_file = tmp_path / f"{job_id}_thumb.jpg"
    thumb_file.write_bytes(b"fake thumb")

    memory_db.executemany(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        [
            (job_id, "render", "done", str(render_file)),
            (job_id, "thumbnail", "done", str(thumb_file)),
        ]
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.error_msg is None


def test_qa_check_render_missing(memory_db, tmp_path):
    job_id = "job_qa_002"

    thumb_file = tmp_path / f"{job_id}_thumb.jpg"
    thumb_file.write_bytes(b"fake thumb")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "thumbnail", "done", str(thumb_file))
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "error"
    assert "render" in result.error_msg


def test_qa_check_empty_render_file(memory_db, tmp_path):
    job_id = "job_qa_003"

    render_file = tmp_path / f"{job_id}_render.mp4"
    render_file.write_bytes(b"")
    thumb_file = tmp_path / f"{job_id}_thumb.jpg"
    thumb_file.write_bytes(b"thumb data")

    memory_db.executemany(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        [
            (job_id, "render", "done", str(render_file)),
            (job_id, "thumbnail", "done", str(thumb_file)),
        ]
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "error"
    assert "empty" in result.error_msg
