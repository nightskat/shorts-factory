# shorts-factory

[![CI](https://github.com/nightskat/shorts-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/nightskat/shorts-factory/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> Turn any idea into a YouTube Short — bring your own LLM, any language, any niche.

## Why this exists

Most hosted tools that turn an idea into a short-form video pick the LLM for you, control the prompts, and charge per render on top of any AI subscription you already pay for. `shorts-factory` is the opposite: you bring your own API keys, the pipeline runs locally, every step is idempotent, and the code is small enough to read end to end.

If you already pay for an LLM subscription, you shouldn't have to pay again to render a video.

## Status

Alpha. The pipeline runs end-to-end against mocks, and the core infrastructure (job model, lease semantics, step runner, HITL gate) has unit-test coverage. Known gaps:

- `upload_yt` — YouTube Data API v3 call is a placeholder
- `bgm_mix`, `clips`, `render` — invoke real ffmpeg/Pexels but lack end-to-end test coverage
- Web UI — minimal HTML/Jinja2, no production hardening

The architecture is settled; integration work and hardening remain. Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for areas where help is most useful.

## What's distinctive

1. **Bring your own LLM** — OpenRouter (default), OpenAI, Anthropic, Gemini, or local Ollama. No hardcoded provider.
2. **Human-in-the-loop gate** — scripts can be reviewed before any render budget is spent.
3. **Idempotent pipeline** — every step records its result; a job can resume from the last successful step after a crash.
4. **Few-shot voice anchoring** — approved scripts are stored and replayed as examples on subsequent generations, so the output stays in a consistent voice over time.

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
# Fill OPENROUTER_API_KEY and any other keys
docker compose up
# Web UI at http://localhost:8765
```

### Local

```bash
pip install -e ".[web,cli]"
cp .env.example .env
shorts-factory serve
# Web UI at http://localhost:8765
```

For local development (running the test suite), install the dev extras as well:

```bash
pip install -e ".[web,cli,dev]"
pytest tests/ -q
```

Minimum required env:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
```

Everything else has sensible defaults. See `.env.example` for full reference.

## Pipeline Steps

| Step | What it does | Status |
|------|--------------|--------|
| `idea_gen` | LLM generates a short-form script from your prompt | working |
| `tts` | Edge-TTS (free) converts script to speech audio | working |
| `bgm_mix` | Mix optional background music under the voiceover | working |
| `scenes` | LLM splits script into timed visual scenes | working |
| `clips` | Fetch matching stock footage from Pexels | working |
| `render` | ffmpeg assembles clips + audio into final .mp4 | working |
| `thumbnail` | Extract best thumbnail frame from rendered video | working |
| `qa_check` | Validate output files (duration, bitrate, resolution) | working |
| `upload_yt` | YouTube Data API v3 — upload + set title/tags/category | **stubbed** |

Steps are idempotent. A failed step can be reset and retried without re-running earlier steps.

## CLI

```bash
shorts-factory serve                         # Start web UI at localhost:8765
shorts-factory run <job-id>                  # Run all pending steps for a job
shorts-factory step reset <job-id> <step>    # Reset a single step to pending
shorts-factory voice seed --content "..."    # Add an approved script as voice example
shorts-factory voice --list                  # List available TTS voices
```

## Architecture

```
shorts/
  pipeline.py — job model, step runner, lease + rerun semantics
  db.py       — SQLite schema + init
  nodes/      — one file per pipeline step
  providers/  — LLM, TTS, clips provider interfaces + implementations
  voice/      — few-shot voice example management
  web/        — FastAPI routes + Jinja2 templates
  cli.py      — Typer CLI entry point
```

Each step acquires a SQLite-backed lease before executing. If a runner crashes, the lease expires after a timeout and another runner can pick the step up. Human-in-the-loop checkpoints pause execution until the artifact is approved.

**Requirements:** Python 3.11+, ffmpeg, and an LLM API key (OpenRouter by default).

## Roadmap

In rough priority order:

- [ ] Real YouTube Data API v3 wiring in `shorts/nodes/upload_yt.py`
- [ ] End-to-end integration test with real ffmpeg and Pexels
- [ ] Human-in-the-loop approval surfaced in the web UI (currently only DB / CLI)
- [ ] Crash-recovery reconciliation flow for partially-completed uploads
- [ ] Idea ingestion sources (RSS, YouTube channel feeds)
- [ ] Additional LLM providers (Anthropic native, local Ollama)
- [ ] Additional TTS providers (ElevenLabs, Kokoro)
- [x] GitHub Actions CI (Linux + macOS, Python 3.11/3.12)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and the areas where help is most useful. Issues and PRs are welcome. The design notes live under `specs/`.

## License

MIT — see [LICENSE](LICENSE).
