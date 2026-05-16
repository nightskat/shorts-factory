from shorts.db import init_db
from shorts.config import DB_PATH
from shorts.utils.rollout import log_checkpoint

def test_scaffold_integrity(tmp_path):
    # Simulate full bootstrap
    test_db = tmp_path / "smoke.db"
    init_db(str(test_db))
    log_checkpoint("smoke_test", "passed")
    assert test_db.exists()
