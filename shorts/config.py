import os
import json
import socket
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("SHORTS_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "shorts.db"
ROLLOUT_JSONL = DATA_DIR / "rollouts" / "build-cycle.jsonl"

WEB_BIND = os.getenv("WEB_BIND", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8765"))

LEASE_HEARTBEAT_SEC = 30
LEASE_STALE_SEC = 120

def get_lease_owner() -> str:
    return f"{os.getpid()}@{socket.gethostname()}"

def snapshot_execution_context(job_id: str, extra_params: dict = None) -> str:
    # Capture all SHORTS_* and relevant provider env vars
    sensitive_keywords = ["KEY", "SECRET", "TOKEN", "PASSWORD", "API"]
    env_snapshot = {}
    for k, v in os.environ.items():
        if k.startswith("SHORTS_") or k.startswith("LLM_") or k.startswith("TTS_"):
            if any(kw in k.upper() for kw in sensitive_keywords):
                env_snapshot[k] = "***MASKED***"
            else:
                env_snapshot[k] = v

    
    snapshot = {
        "job_id": job_id,
        "timestamp": str(datetime.now()),
        "lease_owner": get_lease_owner(),
        "env": env_snapshot
    }
    if extra_params:
        snapshot.update(extra_params)
    return json.dumps(snapshot)
