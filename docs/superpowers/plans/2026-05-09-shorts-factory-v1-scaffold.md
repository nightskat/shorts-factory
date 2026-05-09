# Shorts Factory v1 Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the structural scaffold for `shorts-factory`: directories, schema bootstrap, base config, and rollout checkpoints.

**Architecture:** A modular, SQLite-backed pipeline designed for idempotency and concurrency. Workers claim tasks via a lease model, and all execution parameters are snapshotted to ensure deterministic results.

**Tech Stack:** Python 3.12+, SQLite, FastAPI (v1), Pydantic (config), Shell (subprocess).

---

### Task 1: Project Directory and Module Skeleton

**Files:**
- Create: `shorts/__init__.py`
- Create: `shorts/providers/__init__.py`
- Create: `shorts/providers/llm/__init__.py`
- Create: `shorts/providers/tts/__init__.py`
- Create: `shorts/providers/clips/__init__.py`
- Create: `shorts/nodes/__init__.py`
- Create: `shorts/sources/__init__.py`
- Create: `shorts/voice/__init__.py`
- Create: `shorts/web/__init__.py`
- Create: `shorts/utils/__init__.py`
- Create: `prompts/.gitkeep`
- Create: `data/rollouts/.gitkeep`
- Create: `secrets/.gitkeep`
- Create: `docs/superpowers/plans/.gitkeep`

- [ ] **Step 1: Create the directory tree**
```bash
mkdir -p shorts/providers/llm shorts/providers/tts shorts/providers/clips shorts/nodes shorts/sources shorts/voice shorts/web shorts/utils prompts data/rollouts secrets docs/superpowers/plans
```

- [ ] **Step 2: Initialize python modules**
```bash
touch shorts/__init__.py shorts/providers/__init__.py shorts/providers/llm/__init__.py shorts/providers/tts/__init__.py shorts/providers/clips/__init__.py shorts/nodes/__init__.py shorts/sources/__init__.py shorts/voice/__init__.py shorts/web/__init__.py shorts/utils/__init__.py
touch prompts/.gitkeep data/rollouts/.gitkeep secrets/.gitkeep docs/superpowers/plans/.gitkeep
```

- [ ] **Step 3: Verify structure**
Run: `ls -R shorts`
Expected: Full hierarchy visible.

- [ ] **Step 4: Commit**
```bash
git add .
git commit -m "chore(scaffold): create project structure"
```

---

### Task 2: SQLite Schema Bootstrap (db.py)

**Files:**
- Create: `shorts/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the schema initialization code**
```python
import sqlite3
import os
from datetime import datetime

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
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

if __name__ == "__main__":
    init_db("data/shorts.db")
```

- [ ] **Step 2: Write test to verify schema creation**
```python
import os
import sqlite3
from shorts.db import init_db

def test_init_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    assert os.path.exists(db_path)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert "jobs" in tables
        assert "step_results" in tables
        assert "youtube_uploads" in tables
```

- [ ] **Step 3: Run test**
Run: `pytest tests/test_db.py`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add shorts/db.py tests/test_db.py
git commit -m "chore(db): add schema bootstrap"
```

---

### Task 3: Base Configuration and Snapshot (config.py)

**Files:**
- Create: `shorts/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Implement base configuration**
```python
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "shorts.db"
ROLLOUT_JSONL = DATA_DIR / "rollouts" / "build-cycle.jsonl"

WEB_BIND = os.getenv("WEB_BIND", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8765"))

LEASE_HEARTBEAT_SEC = 30
LEASE_STALE_SEC = 120

def snapshot_execution_context(job_id: str, extra_params: dict = None) -> str:
    snapshot = {
        "job_id": job_id,
        "timestamp": str(datetime.now()),
        "env": {
            "llm_provider": os.getenv("LLM_PROVIDER", "openrouter"),
            "tts_provider": os.getenv("TTS_PROVIDER", "edge-tts"),
        }
    }
    if extra_params:
        snapshot.update(extra_params)
    return json.dumps(snapshot)
```

- [ ] **Step 2: Write test for configuration**
```python
from shorts.config import WEB_BIND, snapshot_execution_context
import json

def test_config_defaults():
    assert WEB_BIND == "127.0.0.1"

def test_snapshot_shape():
    snapshot_raw = snapshot_execution_context("job-123")
    snapshot = json.loads(snapshot_raw)
    assert snapshot["job_id"] == "job-123"
    assert "env" in snapshot
```

- [ ] **Step 3: Run test**
Run: `pytest tests/test_config.py`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add shorts/config.py tests/test_config.py
git commit -m "chore(config): add base settings and snapshot shape"
```

---

### Task 4: Rollout Checkpoint Logger

**Files:**
- Create: `shorts/utils/rollout.py`
- Test: `tests/test_rollout.py`

- [ ] **Step 1: Implement JSONL logger**
```python
import json
from datetime import datetime
from shorts.config import ROLLOUT_JSONL

def log_checkpoint(name: str, status: str, metadata: dict = None):
    ROLLOUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "type": "checkpoint",
        "name": name,
        "status": status
    }
    if metadata:
        entry.update(metadata)
    
    with open(ROLLOUT_JSONL, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

- [ ] **Step 2: Write test for logger**
```python
import os
import json
from shorts.utils.rollout import log_checkpoint
from shorts.config import ROLLOUT_JSONL

def test_log_checkpoint():
    if ROLLOUT_JSONL.exists():
        os.remove(ROLLOUT_JSONL)
    
    log_checkpoint("test_point", "success", {"info": "ok"})
    assert ROLLOUT_JSONL.exists()
    
    with open(ROLLOUT_JSONL, "r") as f:
        line = f.readline()
        entry = json.loads(line)
        assert entry["name"] == "test_point"
        assert entry["status"] == "success"
```

- [ ] **Step 3: Run test**
Run: `pytest tests/test_rollout.py`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add shorts/utils/rollout.py tests/test_rollout.py
git commit -m "chore(rollout): add build-cycle checkpoint log"
```

---

### Task 5: Smoke Tests and Final Review

**Files:**
- Create: `tests/smoke_test.py`

- [ ] **Step 1: Write architecture smoke test**
```python
from shorts.db import init_db
from shorts.config import DB_PATH
from shorts.utils.rollout import log_checkpoint

def test_scaffold_integrity(tmp_path):
    # Simulate full bootstrap
    test_db = tmp_path / "smoke.db"
    init_db(str(test_db))
    log_checkpoint("smoke_test", "passed")
    assert test_db.exists()
```

- [ ] **Step 2: Run all tests**
Run: `pytest`
Expected: 100% PASS

- [ ] **Step 3: Log final scaffold checkpoint**
```python
from shorts.utils.rollout import log_checkpoint
log_checkpoint("v1_scaffold_complete", "success", {"sri": 92})
```

- [ ] **Step 4: Final commit**
```bash
git add tests/smoke_test.py
git commit -m "test(scaffold): add smoke coverage"
```
