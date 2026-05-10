# qa_check.py — verify render and thumbnail outputs exist and are non-empty
import os
import sqlite3
from typing import Any
from shorts.nodes import StepResult


def run(job_id: str, execution_context: dict[str, Any], db_conn: sqlite3.Connection, services: dict[str, Any]) -> StepResult:
    cursor = db_conn.cursor()

    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "render")
    )
    render_row = cursor.fetchone()

    cursor.execute(
        "SELECT output_path FROM step_results WHERE job_id = ? AND step_name = ? AND status = 'done'",
        (job_id, "thumbnail")
    )
    thumb_row = cursor.fetchone()

    errors = []

    if not render_row or not render_row[0]:
        errors.append("render output not found")
    elif not os.path.exists(render_row[0]):
        errors.append(f"render file missing: {render_row[0]}")
    elif os.path.getsize(render_row[0]) == 0:
        errors.append("render file is empty")

    if not thumb_row or not thumb_row[0]:
        errors.append("thumbnail output not found")
    elif not os.path.exists(thumb_row[0]):
        errors.append(f"thumbnail file missing: {thumb_row[0]}")
    elif os.path.getsize(thumb_row[0]) == 0:
        errors.append("thumbnail file is empty")

    if errors:
        return StepResult(status="error", error_msg="; ".join(errors))

    return StepResult(status="done")
