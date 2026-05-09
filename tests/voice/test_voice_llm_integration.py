import pytest
from unittest.mock import MagicMock, patch
from shorts.voice.examples import get_top_examples, add_seed_example
from shorts.voice.injector import inject_voice_into_system_prompt
from shorts.providers.llm.base import LLMProvider

def test_voice_injector_llm_integration(tmp_path):
    # Use a temporary database path for tests
    db_path = tmp_path / "test_shorts.db"
    
    with patch("shorts.config.DB_PATH", db_path), \
         patch("shorts.voice.examples._get_db_path", return_value=str(db_path)):
        
        # Initialize DB schema
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE voice_examples (id INTEGER PRIMARY KEY, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE TABLE approved_scripts (id INTEGER PRIMARY KEY, script_body TEXT, edit_delta TEXT, approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

        # 1. Add examples to voice store
        add_seed_example("This is a high-energy script example.")
        add_seed_example("This is a calm and professional example.")
        
        # 2. Retrieve top examples
        examples = get_top_examples(limit=2)
        assert len(examples) == 2
        
        # 3. Inject into system prompt
        base_prompt = "You are a script writer. {{VOICE_EXAMPLES}}"
        system_prompt = inject_voice_into_system_prompt(base_prompt, examples)
        
        assert "high-energy" in system_prompt
        assert "calm and professional" in system_prompt
        
        # 4. Pass to Mock LLM Provider
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.complete.return_value = "Generated script following the voice."
        
        user_input = "Write a script about space travel."
        response = mock_provider.complete(system=system_prompt, user=user_input)
        
        assert response == "Generated script following the voice."
        mock_provider.complete.assert_called_once_with(system=system_prompt, user=user_input)
