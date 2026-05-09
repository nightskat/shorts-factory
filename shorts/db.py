import os
import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT DEFAULT 'draft',
    execution_context JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS step_results (
    job_id TEXT,
    step_name TEXT,
    status TEXT DEFAULT 'pending',
    input_hash TEXT,
    config_hash TEXT,
    provider_id TEXT,
    output_path TEXT,
    output_checksum TEXT,
    output_bytes INTEGER,
    started_at DATETIME,
    finished_at DATETIME,
    lease_owner TEXT,
    lease_heartbeat_at INTEGER,
    attempt_id TEXT,
    PRIMARY KEY (job_id, step_name),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS voice_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approved_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_body TEXT,
    edit_delta TEXT,
    approved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS youtube_uploads (
    job_id TEXT PRIMARY KEY,
    idempotency_key TEXT,
    status TEXT,
    video_id TEXT,
    resumable_session_url TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
"""

def init_db(db_path: str):
    """Initializes the SQLite database with the required schema."""
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.executescript(SCHEMA)
