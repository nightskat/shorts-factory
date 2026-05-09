from typing import List

def format_few_shot(examples: List[str]) -> str:
    """Format each example with clear delimiters and deterministic ordering."""
    if not examples:
        return ""
    
    blocks = []
    # Ensure deterministic output by sorting examples
    for example in sorted(examples):
        block = f"### EXAMPLE START ###\n{example.strip()}\n### EXAMPLE END ###"
        blocks.append(block)
    
    return "\n\n".join(blocks)

def inject_voice_into_system_prompt(base_prompt: str, examples: List[str]) -> str:
    """Inject formatted few-shot examples into the system prompt."""
    few_shot_block = format_few_shot(examples)
    if not few_shot_block:
        return base_prompt
    
    # Support placeholder replacement or default to appending
    if "{{VOICE_EXAMPLES}}" in base_prompt:
        return base_prompt.replace("{{VOICE_EXAMPLES}}", few_shot_block)
    
    return f"{base_prompt.strip()}\n\nFew-shot voice examples:\n{few_shot_block}"
