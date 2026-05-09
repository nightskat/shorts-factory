# Shorts Factory Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement base configuration and the execution context snapshotting helper in `shorts/config.py` and write a test.

**Architecture:** A simple configuration module using `pathlib` for directory paths and `os.getenv` for environment variables, plus a JSON-based execution context snapshotting utility.

**Tech Stack:** Python, pytest, rtk

---

### Task 1: Base Configuration (config.py)

**Files:**
- Create: `shorts/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from shorts.config import BASE_DIR, DATA_DIR, DB_PATH, ROLLOUT_JSONL, WEB_BIND, WEB_PORT, LEASE_HEARTBEAT_SEC, LEASE_STALE_SEC
from pathlib import Path

def test_config_defaults():
    assert isinstance(BASE_DIR, Path)
    assert BASE_DIR.name == "shorts-factory"
    assert DATA_DIR == BASE_DIR / "data"
    assert DB_PATH == DATA_DIR / "shorts.db"
    assert ROLLOUT_JSONL == DATA_DIR / "rollouts" / "build-cycle.jsonl"
    assert WEB_BIND == "127.0.0.1"
    assert WEB_PORT == 8765
    assert LEASE_HEARTBEAT_SEC == 30
    assert LEASE_STALE_SEC == 120
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_config.py::test_config_defaults -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'shorts.config'" (or similar)

- [ ] **Step 3: Write minimal implementation**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "shorts.db"
ROLLOUT_JSONL = DATA_DIR / "rollouts" / "build-cycle.jsonl"

WEB_BIND = os.getenv("WEB_BIND", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8765"))

LEASE_HEARTBEAT_SEC = 30
LEASE_STALE_SEC = 120
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_config.py::test_config_defaults -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shorts/config.py tests/test_config.py
git commit -m "chore(config): add base settings"
```

---

### Task 2: Execution Context Snapshot (snapshot_execution_context)

**Files:**
- Modify: `shorts/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from shorts.config import snapshot_execution_context

def test_snapshot_execution_context():
    job_id = "test-job-123"
    extra = {"foo": "bar"}
    snapshot_str = snapshot_execution_context(job_id, extra)
    snapshot = json.loads(snapshot_str)
    
    assert snapshot["job_id"] == job_id
    assert "timestamp" in snapshot
    assert snapshot["env"]["llm_provider"] == "openrouter"
    assert snapshot["env"]["tts_provider"] == "edge-tts"
    assert snapshot["foo"] == "bar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_config.py::test_snapshot_execution_context -v`
Expected: FAIL with "ImportError: cannot import name 'snapshot_execution_context' from 'shorts.config'"

- [ ] **Step 3: Write minimal implementation**

```python
import json
from datetime import datetime

# ... (previous code)

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

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_config.py::test_snapshot_execution_context -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shorts/config.py tests/test_config.py
git commit -m "chore(config): add snapshot helper"
```
