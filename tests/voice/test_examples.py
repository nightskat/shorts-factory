import os
import sqlite3
import pytest
from shorts.db import init_db
from shorts.voice.examples import add_seed_example, add_approved_script, get_top_examples
import shorts.config

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_voice.db"
    # Monkeypatch the DB_PATH in config
    original_db_path = shorts.config.DB_PATH
    shorts.config.DB_PATH = db_path
    
    init_db(str(db_path))
    
    yield db_path
    
    # Restore original path
    shorts.config.DB_PATH = original_db_path

def test_add_and_retrieve_examples(temp_db):
    add_seed_example("Seed 1")
    add_approved_script("Approved 1", "delta 1")
    
    examples = get_top_examples(limit=5)
    assert len(examples) == 2
    # Recency sort depends on timestamp; since they are added same second, 
    # the tie-breaker is source_type and source_id.
    # 'seed' comes before 'approved' in DESC order for source_type.
    assert "Seed 1" in examples
    assert "Approved 1" in examples

def test_deterministic_recency_order(temp_db, monkeypatch):
    import time
    
    # Force different timestamps by manual insertion if needed, 
    # but let's try sequential calls first.
    add_seed_example("Older Seed")
    time.sleep(1.1) # Ensure timestamp difference
    add_approved_script("Newer Approved")
    
    examples = get_top_examples(limit=1)
    assert examples[0] == "Newer Approved"

def test_limit_clause(temp_db):
    for i in range(5):
        add_seed_example(f"Content {i}")
    
    examples = get_top_examples(limit=3)
    assert len(examples) == 3
