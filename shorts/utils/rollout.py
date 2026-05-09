import json
from datetime import datetime
from shorts import config

def log_checkpoint(name: str, status: str, metadata: dict = None):
    config.ROLLOUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "type": "checkpoint",
        "name": name,
        "status": status
    }
    if metadata:
        entry.update(metadata)
    
    with open(config.ROLLOUT_JSONL, "a") as f:
        f.write(json.dumps(entry) + "\n")
