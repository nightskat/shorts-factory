# shorts-factory

> Turn any idea into a YouTube Short — bring your own LLM, any language, any niche.

## What it is

A self-hosted, open-source pipeline that automates YouTube Shorts production:

```
idea → script (LLM) → TTS → background music mix → stock clips → render → upload
```

No subscriptions. No locked-in providers. You own the output.

## USPs

1. **Bring Your Own LLM** — OpenRouter (default), OpenAI, Anthropic, Gemini, or local Ollama
2. **HITL gate** — review scripts before burning render time
3. **Idempotent pipeline** — resume any job from any step after a crash
4. **Few-shot voice** — your approved scripts train future generations

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
pip install ".[web,cli]"
cp .env.example .env
shorts-factory serve
# Web UI at http://localhost:8765
```

## Pipeline Steps

| Step | What it does |
|------|--------------|
| `idea_gen` | LLM generates a short-form script from your prompt |
| `tts` | Edge-TTS (free) converts script to speech audio |
| `bgm_mix` | Mix optional background music under the voiceover |
| `scenes` | LLM splits script into timed visual scenes |
| `clips` | Fetch matching stock footage from Pexels |
| `render` | ffmpeg assembles clips + audio into final .mp4 |
| `thumbnail` | Extract best thumbnail frame from rendered video |
| `qa_check` | Validate output files (duration, bitrate, resolution) |
| `upload_yt` | YouTube Data API v3 — upload + set title/tags/category |

Steps are idempotent. A failed step can be reset and retried without re-running earlier steps.

## Configuration

See `.env.example` for all configurable options. Minimum required:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
```

Everything else has sensible defaults.

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
  pipeline/   — job model, step runner, lease + rerun semantics
  nodes/      — one file per pipeline step
  db/         — SQLite schema + queries
  web/        — FastAPI routes + Jinja2 templates
  cli.py      — Typer CLI entry point
```

## Requirements

- Python 3.11+
- ffmpeg (for render step)
- OpenRouter API key (or compatible LLM endpoint)

## License

MIT
