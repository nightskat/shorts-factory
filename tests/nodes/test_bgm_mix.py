import os
from unittest.mock import patch, MagicMock

from shorts.nodes.bgm_mix import run






def test_bgm_mix_skipped_when_no_bgm_path(memory_db, tmp_path):
    job_id = "job_bgm_001"
    execution_context = {"env": {}, "workspace_dir": str(tmp_path)}
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "skipped"


def test_bgm_mix_error_when_no_tts_row(memory_db, tmp_path):
    job_id = "job_bgm_002"
    execution_context = {
        "env": {"BGM_PATH": "/some/bgm.mp3"},
        "workspace_dir": str(tmp_path),
    }
    result = run(job_id, execution_context, memory_db, {})
    assert result.status == "error"
    assert "tts" in result.error_msg


def test_bgm_mix_success(memory_db, tmp_path):
    job_id = "job_bgm_003"

    tts_file = tmp_path / f"{job_id}_tts.mp3"
    tts_file.write_bytes(b"fake tts audio")

    memory_db.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "tts", "done", str(tts_file))
    )
    memory_db.commit()

    bgm_path = str(tmp_path / "bgm.mp3")
    execution_context = {
        "env": {"BGM_PATH": bgm_path},
        "workspace_dir": str(tmp_path),
    }

    def fake_run(cmd, capture_output, timeout):
        # Write a fake mixed file to the tmp path (last positional arg)
        out = cmd[-1]
        with open(out, "wb") as f:
            f.write(b"mixed audio")
        m = MagicMock()
        m.returncode = 0
        return m

    with patch("shorts.nodes.bgm_mix.subprocess.run", side_effect=fake_run):
        result = run(job_id, execution_context, memory_db, {})

    assert result.status == "done"
    assert result.output_path.endswith("_mixed.mp3")
    assert os.path.exists(result.output_path)
    assert result.output_checksum is not None
