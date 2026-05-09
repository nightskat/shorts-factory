import sqlite3
import pytest
import json
from shorts.pipeline import Pipeline
from shorts.db import init_db

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path

def test_pipeline_sequence():
    pipeline = Pipeline()
    assert pipeline.STEPS == [
        "idea_gen",
        "tts",
        "bgm_mix",
        "scenes",
        "clips",
        "render",
        "thumbnail",
        "upload_yt"
    ]

def test_get_runnable_steps_empty():
    pipeline = Pipeline()
    assert pipeline.get_runnable_steps(set()) == ["idea_gen"]

def test_get_runnable_steps_partial():
    pipeline = Pipeline()
    completed = {"idea_gen", "tts"}
    assert pipeline.get_runnable_steps(completed) == ["bgm_mix"]

def test_get_runnable_steps_complete():
    pipeline = Pipeline()
    completed = {
        "idea_gen", "tts", "bgm_mix", "scenes",
        "clips", "render", "thumbnail", "upload_yt"
    }
    assert pipeline.get_runnable_steps(completed) == []

def test_is_complete():
    pipeline = Pipeline()
    assert not pipeline.is_complete(set())
    completed = {
        "idea_gen", "tts", "bgm_mix", "scenes",
        "clips", "render", "thumbnail", "upload_yt"
    }
    assert pipeline.is_complete(completed)

def test_get_runnable_steps_out_of_order():
    pipeline = Pipeline()
    completed = {"tts"}  # idea_gen missing
    assert pipeline.get_runnable_steps(completed) == ["idea_gen"]

def test_promote_job_freezes_context(db_path, monkeypatch):
    pipeline = Pipeline(db_path=db_path)
    job_id = "test-job-1"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (id, status) VALUES (?, ?)",
            (job_id, "draft")
        )
        conn.commit()

    monkeypatch.setenv("SHORTS_TEST_VAR", "original-value")
    pipeline.promote_job(job_id)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

        assert job["status"] == "pending_script"
        assert job["execution_context"] is not None

        context = json.loads(job["execution_context"])
        assert context["env"]["SHORTS_TEST_VAR"] == "original-value"

    monkeypatch.setenv("SHORTS_TEST_VAR", "changed-value")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        context = json.loads(job["execution_context"])
        assert context["env"]["SHORTS_TEST_VAR"] == "original-value"

def test_promote_job_non_existent(db_path):
    pipeline = Pipeline(db_path=db_path)
    with pytest.raises(ValueError, match="Job not found"):
        pipeline.promote_job("non-existent")

def test_promote_job_already_promoted_raises(db_path):
    pipeline = Pipeline(db_path=db_path)
    job_id = "test-job-2"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (id, status) VALUES (?, ?)",
            (job_id, "pending_script")
        )
        conn.commit()

    with pytest.raises(ValueError, match="only 'draft' jobs can be promoted"):
        pipeline.promote_job(job_id)

def test_promote_job_idempotent_guard(db_path):
    pipeline = Pipeline(db_path=db_path)
    job_id = "test-job-3"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (id, status) VALUES (?, ?)",
            (job_id, "draft")
        )
        conn.commit()

    pipeline.promote_job(job_id)

    with sqlite3.connect(db_path) as conn:
        job = conn.execute("SELECT execution_context FROM jobs WHERE id = ?", (job_id,)).fetchone()
        first_snapshot = job[0]

    with pytest.raises(ValueError, match="only 'draft' jobs can be promoted"):
        pipeline.promote_job(job_id)

    with sqlite3.connect(db_path) as conn:
        job = conn.execute("SELECT execution_context FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert job[0] == first_snapshot

@pytest.mark.parametrize("status", ["processing", "pending_upload", "completed", "failed"])
def test_promote_job_non_draft_status_raises(db_path, status):
    pipeline = Pipeline(db_path=db_path)
    job_id = f"test-job-{status}"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO jobs (id, status) VALUES (?, ?)",
            (job_id, status)
        )
        conn.commit()

    with pytest.raises(ValueError, match="only 'draft' jobs can be promoted"):
        pipeline.promote_job(job_id)


# --- Task 3 tests ---

def _insert_job(db_path, job_id, status="draft"):
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO jobs (id, status) VALUES (?, ?)", (job_id, status))
        conn.commit()


def test_claim_step_winner_take_all(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-claim-1")

    assert pipeline.claim_step("job-claim-1", "idea_gen") is True
    assert pipeline.claim_step("job-claim-1", "idea_gen") is False


def test_claim_step_done_blocks_reclaim(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-claim-2")

    pipeline.claim_step("job-claim-2", "idea_gen")
    pipeline.complete_step("job-claim-2", "idea_gen")

    assert pipeline.claim_step("job-claim-2", "idea_gen") is False


def test_claim_step_failed_allows_reclaim(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-claim-3")

    pipeline.claim_step("job-claim-3", "idea_gen")
    pipeline.fail_step("job-claim-3", "idea_gen", "timeout")

    assert pipeline.claim_step("job-claim-3", "idea_gen") is True


def test_claim_step_expired_lease_allows_takeover(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-claim-4")

    pipeline.claim_step("job-claim-4", "idea_gen")

    # Backdate heartbeat to simulate expired lease (>120s ago)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE step_results SET lease_heartbeat_at = STRFTIME('%s', 'now') - 200 "
            "WHERE job_id='job-claim-4' AND step_name='idea_gen'"
        )
        conn.commit()

    assert pipeline.claim_step("job-claim-4", "idea_gen") is True


def test_run_step_success(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-run-1")

    result = pipeline.run_step("job-run-1", "idea_gen", lambda: "script output")

    assert result == "script output"
    assert pipeline.resolve_step_state("job-run-1", "idea_gen") == "done"


def test_run_step_failure_marks_failed(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-run-2")

    def bad_fn():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        pipeline.run_step("job-run-2", "idea_gen", bad_fn)

    assert pipeline.resolve_step_state("job-run-2", "idea_gen") == "failed"


def test_run_step_no_lease_raises(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-run-3")

    # First claim so the second cannot acquire it
    pipeline.claim_step("job-run-3", "idea_gen")

    with pytest.raises(RuntimeError, match="Could not acquire lease"):
        pipeline.run_step("job-run-3", "idea_gen", lambda: None)


# --- Task 4 tests ---

def test_resolve_step_state_pending(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-state-1")
    assert pipeline.resolve_step_state("job-state-1", "idea_gen") == "pending"


def test_resolve_step_state_running(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-state-2")
    pipeline.claim_step("job-state-2", "idea_gen")
    assert pipeline.resolve_step_state("job-state-2", "idea_gen") == "running"


def test_resolve_step_state_done(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-state-3")
    pipeline.claim_step("job-state-3", "idea_gen")
    pipeline.complete_step("job-state-3", "idea_gen")
    assert pipeline.resolve_step_state("job-state-3", "idea_gen") == "done"


def test_skip_step_marks_skipped(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-skip-1")
    pipeline.skip_step("job-skip-1", "bgm_mix", "no music needed")
    assert pipeline.resolve_step_state("job-skip-1", "bgm_mix") == "skipped"


def test_skip_step_idempotent(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-skip-2")
    pipeline.skip_step("job-skip-2", "bgm_mix", "reason 1")
    pipeline.skip_step("job-skip-2", "bgm_mix", "reason 2")
    assert pipeline.resolve_step_state("job-skip-2", "bgm_mix") == "skipped"


def test_get_completed_steps_empty(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-complete-1")
    assert pipeline.get_completed_steps("job-complete-1") == set()


def test_get_completed_steps_includes_done_and_skipped(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-complete-2")

    pipeline.claim_step("job-complete-2", "idea_gen")
    pipeline.complete_step("job-complete-2", "idea_gen")
    pipeline.skip_step("job-complete-2", "bgm_mix", "skipped")
    pipeline.claim_step("job-complete-2", "tts")
    pipeline.fail_step("job-complete-2", "tts", "error")

    completed = pipeline.get_completed_steps("job-complete-2")
    assert completed == {"idea_gen", "bgm_mix"}
    assert "tts" not in completed


def test_get_completed_steps_drives_runnable(db_path):
    pipeline = Pipeline(db_path=db_path)
    _insert_job(db_path, "job-complete-3")

    pipeline.claim_step("job-complete-3", "idea_gen")
    pipeline.complete_step("job-complete-3", "idea_gen")
    pipeline.claim_step("job-complete-3", "tts")
    pipeline.complete_step("job-complete-3", "tts")

    completed = pipeline.get_completed_steps("job-complete-3")
    assert pipeline.get_runnable_steps(completed) == ["bgm_mix"]
