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

import json
from datetime import datetime

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
