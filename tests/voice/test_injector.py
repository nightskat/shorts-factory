from shorts.voice.injector import format_few_shot, inject_voice_into_system_prompt

def test_format_few_shot_empty():
    assert format_few_shot([]) == ""

def test_format_few_shot_multiple():
    examples = ["Example B", "Example A"]
    result = format_few_shot(examples)
    # Check for deterministic sorting (A before B) and delimiters
    assert "### EXAMPLE START ###\nExample A\n### EXAMPLE END ###" in result
    assert "### EXAMPLE START ###\nExample B\n### EXAMPLE END ###" in result
    assert result.index("Example A") < result.index("Example B")

def test_inject_no_placeholder():
    base = "System prompt."
    examples = ["Ex"]
    result = inject_voice_into_system_prompt(base, examples)
    assert "System prompt." in result
    assert "Few-shot voice examples:" in result
    assert "### EXAMPLE START ###\nEx\n### EXAMPLE END ###" in result

def test_inject_with_placeholder():
    base = "Voice: {{VOICE_EXAMPLES}} End."
    examples = ["Ex"]
    result = inject_voice_into_system_prompt(base, examples)
    assert result == "Voice: ### EXAMPLE START ###\nEx\n### EXAMPLE END ### End."
