"""
tests/test_cli.py — Typer CLI tests for the `voice` and `step` subcommands.

Uses typer.testing.CliRunner with a temporary DB (monkeypatched via shorts.config.DB_PATH)
so tests are fully isolated.
"""

import sqlite3
import pytest
from typer.testing import CliRunner
from shorts.cli import app as cli_app


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Patch shorts.config.DB_PATH and shorts.cli.DB_PATH to a fresh tmp DB."""
    db_path = tmp_path / "cli_test.db"
    monkeypatch.setattr("shorts.config.DB_PATH", db_path)
    monkeypatch.setattr("shorts.cli.DB_PATH", db_path)
    yield db_path


def test_voice_seed(isolate_db):
    """voice seed --content '...' inserts a row into approved_scripts."""
    runner = CliRunner()
    result = runner.invoke(cli_app, ["voice", "seed", "--content", "test script"])

    assert result.exit_code == 0, result.output
    assert "Voice example added" in result.output

    conn = sqlite3.connect(str(isolate_db))
    rows = conn.execute("SELECT script_body FROM approved_scripts").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "test script"


def test_step_reset(isolate_db):
    """step reset <job_id> <step_name> changes status from done to failed."""
    from shorts.db import init_db

    init_db(str(isolate_db))

    # Seed a done step_results row
    conn = sqlite3.connect(str(isolate_db))
    conn.execute(
        "INSERT INTO jobs (id, title, status, execution_context) VALUES ('job1', 'title', 'draft', '{}')"
    )
    conn.execute(
        "INSERT INTO step_results (job_id, step_name, status) VALUES ('job1', 'idea_gen', 'done')"
    )
    conn.commit()
    conn.close()

    runner = CliRunner()
    result = runner.invoke(cli_app, ["step", "reset", "job1", "idea_gen"])

    assert result.exit_code == 0, result.output
    assert "Reset step idea_gen for job job1" in result.output

    # Verify status changed
    conn = sqlite3.connect(str(isolate_db))
    row = conn.execute(
        "SELECT status FROM step_results WHERE job_id='job1' AND step_name='idea_gen'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "failed"
