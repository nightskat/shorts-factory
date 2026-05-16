import pytest
import os
import sqlite3
from unittest.mock import MagicMock, patch
from shorts.nodes.idea_gen import run
from shorts.nodes import StepResult


def test_run_success(memory_db, tmp_path):
    env = {"LLM_PROVIDER": "dummy"}
    execution_context = {
        "env": env,
        "system_prompt": "You are a script writer.",
        "user_prompt": "Write a script about cats.",
        "few_shot_data": ["Example 1: ...", "Example 2: ..."],
        "workspace_dir": str(tmp_path)
    }

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "This is a script about cats."

    services = {}

    with patch('shorts.nodes.idea_gen.get_llm_provider', return_value=mock_llm) as mock_get_llm:
        with patch('shorts.nodes.idea_gen.inject_voice_into_system_prompt', return_value="Injected Prompt") as mock_inject:
            result = run("job123", execution_context, memory_db, services)

    assert result.status == "done"
    assert result.output_path == os.path.join(str(tmp_path), "data", "scripts", "job123_script.txt")
    assert result.output_checksum is not None

    mock_get_llm.assert_called_once_with("dummy", env)
    mock_inject.assert_called_once_with("You are a script writer.", ["Example 1: ...", "Example 2: ..."])
    mock_llm.generate.assert_called_once_with("Injected Prompt", "Write a script about cats.")

    with open(result.output_path, "r") as f:
        content = f.read()
    assert content == "This is a script about cats."

def test_run_without_few_shot(memory_db, tmp_path):
    env = {"LLM_PROVIDER": "dummy"}
    execution_context = {
        "env": env,
        "system_prompt": "You are a script writer.",
        "user_prompt": "Write a script about cats.",
        "workspace_dir": str(tmp_path)
    }

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "This is a script about cats."

    services = {}

    with patch('shorts.nodes.idea_gen.get_llm_provider', return_value=mock_llm) as mock_get_llm:
        result = run("job124", execution_context, memory_db, services)

    assert result.status == "done"
    assert result.output_path == os.path.join(str(tmp_path), "data", "scripts", "job124_script.txt")
    mock_llm.generate.assert_called_once_with("You are a script writer.", "Write a script about cats.")

def test_run_generates_error_on_missing_prompts(memory_db):
    execution_context = {"env": {}}
    services = {}
    with pytest.raises(KeyError):
        run("job125", execution_context, memory_db, services)
