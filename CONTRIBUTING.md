# Contributing to shorts-factory

This is an early-stage open-source project looking for engineers who want to build something real. The core architecture is stable — what's missing is real integrations and test coverage.

## What we need most

Specific areas where help is wanted right now:

- **YouTube upload** — implement the actual YouTube Data API v3 call in `shorts/nodes/upload_yt.py`. The idempotency logic is already there; the API call is a stub.
- **End-to-end test** — a test that runs the real pipeline with ffmpeg and Pexels (or a Pexels mock). Currently only unit tests and mock-based integration tests exist.
- **Additional LLM providers** — Anthropic native (non-OpenRouter), OpenAI direct, local Ollama. The provider interface is in `shorts/providers/llm/base.py`.
- **Additional TTS providers** — ElevenLabs, Kokoro. Edge-TTS is the only implementation today.
- **Better web UI** — the current UI is minimal HTML/Jinja2. A React or HTMX upgrade would be welcome. Design system: shadcn/ui + Tailwind.

## Dev setup

```bash
git clone https://github.com/nightskat/shorts-factory.git
cd shorts-factory
pip install -e ".[web,cli]"
cp .env.example .env
# Fill at minimum: OPENROUTER_API_KEY
```

## Running tests

```bash
PYTHONPATH=. python -m pytest tests/ -q
```

All 111 tests should pass. If any fail on a clean clone, open an issue.

## Code style

- Follow the patterns already in the codebase — terse, no unnecessary comments
- One file per pipeline node in `shorts/nodes/`
- New nodes must implement the `StepResult` contract from `shorts/nodes/__init__.py`
- No new dependencies without discussion in an issue first

## PR checklist

- [ ] All existing tests pass: `PYTHONPATH=. python -m pytest tests/ -q`
- [ ] New behavior has test coverage
- [ ] Commit message is descriptive (`feat(nodes): implement upload_yt` not `fix stuff`)
- [ ] No secrets, no `.env` files committed
