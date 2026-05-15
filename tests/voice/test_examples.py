import sqlite3
import pytest
from contextlib import closing
from shorts.db import init_db
from shorts.voice.examples import add_seed_example, add_approved_script, get_top_examples
import shorts.config

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_voice.db"
    original_db_path = shorts.config.DB_PATH
    shorts.config.DB_PATH = db_path
    
    init_db(str(db_path))
    
    yield db_path
    
    shorts.config.DB_PATH = original_db_path

def test_add_and_retrieve_examples(temp_db):
    add_seed_example("Seed 1")
    add_approved_script("Approved 1", "delta 1")
    
    examples = get_top_examples(limit=5)
    assert len(examples) == 2
    assert "Seed 1" in examples
    assert "Approved 1" in examples

def test_deterministic_recency_order(temp_db):
    # Manually insert with specific timestamps to verify sort order without time.sleep
    with closing(sqlite3.connect(str(temp_db))) as conn:
        conn.execute(
            "INSERT INTO voice_examples (content, created_at) VALUES (?, ?)",
            ("Older Seed", "2026-05-09 10:00:00")
        )
        conn.execute(
            "INSERT INTO approved_scripts (script_body, approved_at) VALUES (?, ?)",
            ("Newer Approved", "2026-05-09 11:00:00")
        )
        conn.commit()
    
    examples = get_top_examples(limit=1)
    assert examples[0] == "Newer Approved"

def test_limit_clause(temp_db):
    for i in range(5):
        add_seed_example(f"Content {i}")
    
    examples = get_top_examples(limit=3)
    assert len(examples) == 3
