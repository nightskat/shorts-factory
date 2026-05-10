# shorts-factory

> Turn any idea into a YouTube Short — bring your own LLM, any language, any niche.

## Why this exists

Tools like Pictory and InVideo will generate your video, but they pick the LLM, control the prompts, and charge you per render on top of your existing AI subscriptions. This project does the opposite: you bring your own API keys, the pipeline is fully local and hackable, and every step is idempotent — crash at render, resume at render.

The one-line truth: **if you already pay for Claude, GPT, or Gemini, you shouldn't pay again to render a video.**

## Status: alpha / RFC

The pipeline runs end-to-end with mocks. Core infrastructure (job model, lease semantics, step runner, HITL gate) is solid and tested. What's still stubbed:

- `upload_yt` — YouTube Data API v3 call is a no-op placeholder
- `bgm_mix`, `clips`, `render` — call real ffmpeg/Pexels but have no CI coverage yet
- Web UI — minimal HTML/Jinja2, no production hardening

This is a published RFC. The architecture decisions are made; the plumbing needs hands. If you like the design and want to help harden it, read [CONTRIBUTING.md](CONTRIBUTING.md).

## The 4 USPs

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
pip install -e ".[web,cli]"
cp .env.example .env
shorts-factory serve
# Web UI at http://localhost:8765
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

The pipeline uses a lease model: each step acquires a lease before executing. On crash the lease expires and the step can be retried by any runner. The HITL gate blocks execution at configurable checkpoints until a human approves the artifact in the web UI.

**Requirements:** Python 3.11+, ffmpeg, OpenRouter API key (or compatible LLM endpoint).

## Roadmap

What's planned or in progress — roughly in priority order:

- [ ] Real YouTube Data API v3 wiring in `shorts/nodes/upload_yt.py`
- [ ] End-to-end integration test with real ffmpeg + Pexels sandbox
- [ ] HITL gates surfaced in web UI (currently approval is DB-only via CLI)
- [ ] Manual Reconciliation Gate — `shorts-factory recon` for crash recovery review
- [ ] Sources layer — ingestion pipeline from RSS / YouTube channel → `idea_candidates`
- [ ] Additional LLM providers (Anthropic native, local Ollama)
- [ ] Additional TTS providers (ElevenLabs, Kokoro)
- [ ] GitHub Actions CI

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and what help is most needed right now.

PRs welcome. Issues welcome. If you're just exploring the architecture, the `specs/` directory has the design docs.

## License

MIT — see [LICENSE](LICENSE).
