"""
Node contract definitions for the shorts pipeline.
"""
from dataclasses import dataclass
from typing import Callable, Any, Optional
import sqlite3

@dataclass
class StepResult:
    """Standardized output from any pipeline node."""
    status: str  # e.g., 'success', 'error', 'skipped'
    output_path: Optional[str] = None
    output_checksum: Optional[str] = None
    error_msg: Optional[str] = None

# Type hint for a pipeline node function
# Signature: (job_id, execution_context, db_conn, services) -> StepResult
NodeCallable = Callable[[str, dict[str, Any], sqlite3.Connection, dict[str, Any]], StepResult]
