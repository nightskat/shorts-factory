import sqlite3
import pytest
from shorts.db import SCHEMA

@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    yield conn
    conn.close()
