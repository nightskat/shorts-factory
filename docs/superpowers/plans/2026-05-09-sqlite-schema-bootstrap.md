# SQLite Schema Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the SQLite schema initialization code in `shorts/db.py` and write a unit test to verify it.

**Architecture:** A simple Python module using `sqlite3` to execute a multi-statement SQL schema. It ensures the parent directory exists before creating the database file.

**Tech Stack:** Python 3, SQLite3, Pytest.

---

### Task 1: Environment Setup

**Files:**
- Create: `tests/__init__.py`

- [ ] **Step 1: Create tests directory**
- [ ] **Step 2: Create `tests/__init__.py` to make it a package**

### Task 2: Implement Database Initialization (TDD)

**Files:**
- Create: `shorts/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import sqlite3
import pytest
from shorts.db import init_db

def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    
    assert os.path.exists(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    
    expected_tables = {"jobs", "step_results", "voice_examples", "approved_scripts", "youtube_uploads"}
    for table in expected_tables:
        assert table in tables
    
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_db.py`
Expected: `ImportError: cannot import name 'init_db' from 'shorts.db'` (or similar)

- [ ] **Step 3: Implement `init_db` in `shorts/db.py`**

```python
import os
import sqlite3

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
    lease_heartbeat_at DATETIME,
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
    \"\"\"Initializes the SQLite database with the required schema.\"\"\"
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_db.py`
Expected: `1 passed`

- [ ] **Step 5: Add directory creation test case**

```python
def test_init_db_creates_directory(tmp_path):
    db_dir = tmp_path / "nested" / "dir"
    db_path = str(db_dir / "test.db")
    
    init_db(db_path)
    
    assert os.path.exists(db_path)
    assert os.path.exists(db_dir)
```

- [ ] **Step 6: Run all tests**

Run: `rtk pytest tests/test_db.py`
Expected: `2 passed`

- [ ] **Step 7: Commit changes**

```bash
rtk git add shorts/db.py tests/test_db.py tests/__init__.py
rtk git commit -m "chore(db): add schema bootstrap"
```
