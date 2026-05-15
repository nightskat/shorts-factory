import os
import sqlite3
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

def test_init_db_creates_directory(tmp_path):
    db_dir = tmp_path / "nested" / "dir"
    db_path = str(db_dir / "test.db")
    
    init_db(db_path)
    
    assert os.path.exists(db_path)
    assert os.path.exists(db_dir)
