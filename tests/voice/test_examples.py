import sqlite3
import pytest
from contextlib import closing

from shorts.db import SCHEMA
from shorts.voice.examples import add_seed_example, add_approved_script, get_top_examples
import shorts.config

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """
    Setup a temporary database using the global SCHEMA and monkeypatch
    shorts.config.DB_PATH to use this temporary db path.
    """
    db_path = tmp_path / "test_shorts.db"
    
    # Initialize the database with the global schema
    with closing(sqlite3.connect(str(db_path))) as conn:
        with conn:
            conn.executescript(SCHEMA)

    # Monkeypatch the config so the module under test uses our temp DB
    monkeypatch.setattr(shorts.config, "DB_PATH", db_path)
    
    yield db_path

def test_add_seed_example(temp_db):
    """Test adding a seed example to the database."""
    content = "This is a seed example."
    add_seed_example(content)
    
    # Verify it was added directly
    with closing(sqlite3.connect(str(temp_db))) as conn:
        cursor = conn.execute("SELECT content FROM voice_examples")
        results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][0] == content

def test_add_approved_script(temp_db):
    """Test adding an approved script to the database."""
    script_body = "This is an approved script."
    edit_delta = "Some edit delta"
    add_approved_script(script_body, edit_delta)

    # Verify it was added directly
    with closing(sqlite3.connect(str(temp_db))) as conn:
        cursor = conn.execute("SELECT script_body, edit_delta FROM approved_scripts")
        results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][0] == script_body
    assert results[0][1] == edit_delta

def test_add_approved_script_no_delta(temp_db):
    """Test adding an approved script without an edit_delta."""
    script_body = "This is another approved script."
    add_approved_script(script_body)
    
    # Verify it was added directly
    with closing(sqlite3.connect(str(temp_db))) as conn:
        cursor = conn.execute("SELECT script_body, edit_delta FROM approved_scripts")
        results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][0] == script_body
    assert results[0][1] == ""

def test_get_top_examples_empty(temp_db):
    """Test retrieving top examples when the database is empty."""
    results = get_top_examples()
    assert results == []

def test_get_top_examples_sorting(temp_db):
    """Test that get_top_examples retrieves and sorts entries correctly."""
    # Insert multiple records to test sorting
    # Order should be by created_at DESC, source_type DESC, source_id DESC
    # source_type: 'seed' > 'approved' alphabetically

    with closing(sqlite3.connect(str(temp_db))) as conn:
        with conn:
            # Seed 1
            conn.execute(
                "INSERT INTO voice_examples (content, created_at) VALUES (?, ?)",
                ("Seed older", "2024-01-01 10:00:00")
            )
            # Seed 2
            conn.execute(
                "INSERT INTO voice_examples (content, created_at) VALUES (?, ?)",
                ("Seed newer", "2024-01-02 10:00:00")
            )
            # Approved 1
            conn.execute(
                "INSERT INTO approved_scripts (script_body, edit_delta, approved_at) VALUES (?, ?, ?)",
                ("Approved older", "", "2024-01-01 10:00:00")
            )
            # Approved 2
            conn.execute(
                "INSERT INTO approved_scripts (script_body, edit_delta, approved_at) VALUES (?, ?, ?)",
                ("Approved newer", "", "2024-01-03 10:00:00")
            )

    results = get_top_examples(limit=4)

    # Expected order:
    # 1. Approved newer (2024-01-03)
    # 2. Seed newer (2024-01-02)
    # 3. Seed older (2024-01-01, source_type='seed' so it comes before 'approved')
    # 4. Approved older (2024-01-01, source_type='approved')
    
    assert len(results) == 4
    assert results[0] == "Approved newer"
    assert results[1] == "Seed newer"
    assert results[2] == "Seed older"
    assert results[3] == "Approved older"

def test_get_top_examples_limit(temp_db):
    """Test that get_top_examples respects the limit parameter."""
    for i in range(5):
        add_seed_example(f"Seed {i}")

    results = get_top_examples(limit=3)
    assert len(results) == 3
