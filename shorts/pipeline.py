import sqlite3
import threading
import contextlib
from typing import Optional, Callable, Any
from shorts.config import snapshot_execution_context, DB_PATH, get_lease_owner

class Pipeline:
    STEPS = [
        "idea_gen",
        "tts",
        "bgm_mix",
        "scenes",
        "clips",
        "render",
        "thumbnail",
        "upload_yt"
    ]

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)

    def promote_job(self, job_id: str):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            job = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()

            if not job:
                raise ValueError(f"Job not found: {job_id}")

            if job["status"] != "draft":
                raise ValueError(f"Job {job_id} is in status '{job['status']}', only 'draft' jobs can be promoted.")

            context_json = snapshot_execution_context(job_id)

            cursor = conn.execute(
                "UPDATE jobs SET status = 'pending_script', execution_context = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'draft'",
                (context_json, job_id)
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ValueError(f"Race condition detected: Job {job_id} was modified by another process.")

    def get_runnable_steps(self, completed_steps: set[str]) -> list[str]:
        for step in self.STEPS:
            if step not in completed_steps:
                return [step]
        return []

    def is_complete(self, completed_steps: set[str]) -> bool:
        return all(step in completed_steps for step in self.STEPS)

    # --- Task 3: Lease Model ---

    def claim_step(self, job_id: str, step_name: str) -> bool:
        owner = get_lease_owner()
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO step_results (job_id, step_name, status, lease_owner, lease_heartbeat_at) "
                "VALUES (?, ?, 'running', ?, STRFTIME('%s', 'now'))",
                (job_id, step_name, owner)
            )
            conn.commit()

            if cursor.rowcount == 1:
                return True

            cursor = conn.execute(
                "UPDATE step_results SET status='running', lease_owner=?, lease_heartbeat_at=STRFTIME('%s', 'now') "
                "WHERE job_id=? AND step_name=? AND status NOT IN ('done', 'skipped', 'blocked') "
                "AND (status = 'failed' OR (status = 'running' AND CAST(lease_heartbeat_at AS INTEGER) < STRFTIME('%s', 'now') - 120))",
                (owner, job_id, step_name)
            )
            conn.commit()

            return cursor.rowcount == 1

    def _heartbeat_loop(self, job_id: str, step_name: str, stop_event: threading.Event, interval: int = 30):
        while not stop_event.wait(timeout=interval):
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                conn.execute(
                    "UPDATE step_results SET lease_heartbeat_at = STRFTIME('%s', 'now') "
                    "WHERE job_id=? AND step_name=? AND status='running'",
                    (job_id, step_name)
                )
                conn.commit()

    def run_step(self, job_id: str, step_name: str, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        if not self.claim_step(job_id, step_name):
            raise RuntimeError(f"Could not acquire lease for step '{step_name}' on job '{job_id}'")

        stop_event = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(job_id, step_name, stop_event),
            daemon=True
        )
        heartbeat.start()

        try:
            result = fn(*args, **kwargs)
            self.complete_step(job_id, step_name)
            return result
        except Exception as exc:
            self.fail_step(job_id, step_name, str(exc))
            raise
        finally:
            stop_event.set()
            heartbeat.join()

    def complete_step(self, job_id: str, step_name: str, result_json: Optional[str] = None):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "UPDATE step_results SET status='done', output_checksum=?, finished_at=CURRENT_TIMESTAMP "
                "WHERE job_id=? AND step_name=?",
                (result_json, job_id, step_name)
            )
            conn.commit()

    def fail_step(self, job_id: str, step_name: str, error_msg: str):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "UPDATE step_results SET status='failed', finished_at=CURRENT_TIMESTAMP "
                "WHERE job_id=? AND step_name=?",
                (job_id, step_name)
            )
            conn.commit()

    # --- Task 4: Resume/Skip Semantics ---

    def resolve_step_state(self, job_id: str, step_name: str) -> str:
        import time
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT status, lease_heartbeat_at FROM step_results WHERE job_id=? AND step_name=?",
                (job_id, step_name)
            ).fetchone()

        if row is None:
            return "pending"
        
        status, heartbeat = row[0], row[1]
        if status == "running" and heartbeat is not None:
            if int(time.time()) - int(heartbeat) > 120:
                return "failed"
                
        return status

    def skip_step(self, job_id: str, step_name: str, reason: str):
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO step_results (job_id, step_name, status) "
                "VALUES (?, ?, 'skipped') "
                "ON CONFLICT(job_id, step_name) DO UPDATE SET status='skipped', finished_at=CURRENT_TIMESTAMP",
                (job_id, step_name)
            )
            conn.commit()

    def get_completed_steps(self, job_id: str) -> set[str]:
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT step_name FROM step_results WHERE job_id=? AND status IN ('done', 'skipped')",
                (job_id,)
            ).fetchall()
        return {row[0] for row in rows}
