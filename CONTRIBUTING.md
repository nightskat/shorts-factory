# Contributing to shorts-factory

`shorts-factory` is in early development. The architecture is settled, but several integrations remain stubbed and overall test coverage needs to grow. Contributions of any size are welcome.

## Where help is most useful

- **YouTube upload** — implement the YouTube Data API v3 call in `shorts/nodes/upload_yt.py`. The idempotency layer is in place; only the API call itself is a stub.
- **End-to-end pipeline test** — a test that exercises the real pipeline with ffmpeg and Pexels (or a Pexels mock). Today only unit and mock-based tests exist.
- **Additional LLM providers** — Anthropic native (non-OpenRouter), OpenAI direct, local Ollama. The provider interface lives at `shorts/providers/llm/base.py`.
- **Additional TTS providers** — ElevenLabs, Kokoro, or others. Edge-TTS is the only implementation today.
- **Web UI improvements** — the current UI is minimal HTML/Jinja2. An HTMX or React upgrade would be a welcome change.

## Dev setup

```bash
git clone https://github.com/nightskat/shorts-factory.git
cd shorts-factory
pip install -e ".[web,cli,dev]"
cp .env.example .env
# Fill at minimum: OPENROUTER_API_KEY
```

## Running tests

```bash
pytest tests/ -q
```

If any test fails on a clean checkout, please open an issue — that's a real bug.

## Code style

- Follow the patterns already in the codebase: terse, minimal comments.
- One file per pipeline node under `shorts/nodes/`.
- New nodes implement the `StepResult` contract defined in `shorts/nodes/__init__.py`.
- For new runtime dependencies, please open an issue first to discuss.

## Pull requests

- All existing tests pass: `pytest tests/ -q`
- New behaviour comes with test coverage
- Commit messages follow conventional commits (`feat(...)`, `fix(...)`, `docs(...)`, ...)
- No secrets, credentials, or `.env` files committed
