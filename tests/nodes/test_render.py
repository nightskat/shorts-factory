import json
import os
import sqlite3
import pytest

from shorts.nodes.render import run


def test_render_placeholder_clips(memory_db, tmp_path):
    job_id = "job_render_001"

    # Create placeholder clip txt files
    clips_dir = tmp_path / "data" / "clips"
    clips_dir.mkdir(parents=True)
    clip0 = clips_dir / f"{job_id}_clip_0.txt"
    clip0.write_text("scene description 0")

    manifest = [{"clip_path": str(clip0), "duration_seconds": 5}]
    clips_file = clips_dir / f"{job_id}_clips.json"
    clips_file.write_text(json.dumps(manifest))

    tts_file = tmp_path / f"{job_id}_tts.mp3"
    tts_file.write_bytes(b"fake audio")

    memory_db.executemany(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        [
            (job_id, "clips", "done", str(clips_file)),
            (job_id, "tts", "done", str(tts_file)),
        ],
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path.endswith("_render.mp4")
    assert os.path.exists(result.output_path)
    assert result.output_checksum is not None


def test_render_uses_bgm_mix_audio_when_available(memory_db, tmp_path):
    job_id = "job_render_002"

    clips_dir = tmp_path / "data" / "clips"
    clips_dir.mkdir(parents=True)
    clip0 = clips_dir / f"{job_id}_clip_0.txt"
    clip0.write_text("scene")

    manifest = [{"clip_path": str(clip0), "duration_seconds": 5}]
    clips_file = clips_dir / f"{job_id}_clips.json"
    clips_file.write_text(json.dumps(manifest))

    mixed_file = tmp_path / f"{job_id}_mixed.mp3"
    mixed_file.write_bytes(b"mixed audio")

    memory_db.executemany(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        [
            (job_id, "clips", "done", str(clips_file)),
            (job_id, "bgm_mix", "done", str(mixed_file)),
        ],
    )
    memory_db.commit()

    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert os.path.exists(result.output_path)


def test_render_missing_clips(memory_db, tmp_path):
    job_id = "job_render_003"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
