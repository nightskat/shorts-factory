import sqlite3
from typing import List, Optional
from contextlib import closing
import shorts.config

def _get_db_path() -> str:
    return str(shorts.config.DB_PATH)

def add_seed_example(content: str) -> None:
    """Add a seed script example to the database."""
    with closing(sqlite3.connect(_get_db_path())) as conn:
        with conn:
            conn.execute("INSERT INTO voice_examples (content) VALUES (?)", (content,))

def add_approved_script(script_body: str, edit_delta: Optional[str] = "") -> None:
    """Add an approved script to the database."""
    with closing(sqlite3.connect(_get_db_path())) as conn:
        with conn:
            conn.execute("INSERT INTO approved_scripts (script_body, edit_delta) VALUES (?, ?)", (script_body, edit_delta))

def get_top_examples(limit: int = 3) -> List[str]:
    """
    Retrieve the top N examples, merged from seeds and approved scripts, 
    sorted deterministically by recency.
    """
    query = """
        SELECT content, created_at, id as source_id, 'seed' as source_type
        FROM voice_examples
        UNION ALL
        SELECT script_body as content, approved_at as created_at, id as source_id, 'approved' as source_type
        FROM approved_scripts
        ORDER BY created_at DESC, source_type DESC, source_id DESC
        LIMIT ?
    """
    with closing(sqlite3.connect(_get_db_path())) as conn:
        cursor = conn.execute(query, (limit,))
        return [row[0] for row in cursor.fetchall()]
