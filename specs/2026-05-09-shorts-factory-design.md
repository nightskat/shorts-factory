# shorts-factory — Design Spec v1.0

**Date:** 2026-05-09
**Status:** Draft — pending user review
**Author:** Tuan Khuc + Claude

---

## 1. Positioning

### Tagline
> "Turn any idea into a YouTube Short — bring your own LLM, any language, any niche."

### What it is
`shorts-factory` is an open-source, self-hosted pipeline that automates YouTube Shorts creation end-to-end: idea sourcing → script generation → TTS → video render → YouTube upload.

### What it is NOT (v1)
- Not a SaaS product (that comes later)
- Not a clip-from-existing-video tool (Opus Clip territory)
- Not an AI actor / talking head tool

### Target users
- **Primary:** Developers who self-host, configure `.env`, run Docker
- **Secondary:** Technical content creators comfortable with Docker

### Origin
Extracted and generalized from `youtube-meo` (private repo — a Vietnamese cat Shorts channel pipeline). The private repo remains as internal reference; this public repo is a clean rewrite.

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
Most repos hardcode one provider and require a separate API key — even if you already pay for Claude Pro or Gemini AI Pro.

`shorts-factory` supports two access modes:
- **API key mode** — OpenRouter (default, 100+ models, 1 key), OpenAI, Anthropic, Gemini, Ollama local
- **CLI subscription mode** — use your existing subscription via CLI subprocess (zero extra billing):
  - `LLM_PROVIDER=claude-cli` → uses Claude Pro via `claude` CLI
  - `LLM_PROVIDER=gemini-cli` → uses Google AI Pro via `gemini` CLI
  - `LLM_PROVIDER=codex-cli` → uses Codex subscription via `codex` CLI

### USP 2 — HITL gate (script review before burning resources)
All competing repos run fully automated — no review before TTS + render. `shorts-factory` pauses at `script_pending` state, lets the user read and approve, then continues. Prevents wasted renders on bad scripts.

### USP 3 — Idempotent pipeline (resume from any step)
Each pipeline step logs its result. Re-running a job skips already-completed steps. Delete a specific output file to force re-run of that step only. No competing repo does this.

### USP 4 — Author Voice (learns your style over time)
The system accumulates a voice profile from:
- **Seeds:** user-written script samples (`shorts voice seed`)
- **Notes/salting:** per-idea style notes (`shorts add "title" --note "..."`)
- **Edit loop:** every approved script edit is stored with increasing weight

Future `idea_gen` calls inject the top N approved scripts as few-shot examples → output gradually matches the user's voice without fine-tuning.

---

## 3. Philosophy

**Free by default, configurable everything.**

| Layer | Free default | Configurable alternatives |
|---|---|---|
| Idea sources | Google Trends + LLM-generated | Reddit, YouTube API, RSS, custom |
| LLM | OpenRouter (user provides key) | OpenAI, Anthropic, Gemini, Ollama, CLI subs |
| TTS | Edge-TTS (free, 300+ voices) | ElevenLabs, OpenAI TTS |
| Clips | Pexels free tier | Pixabay, local folder |
| Publish | YouTube Data API v3 | `--no-publish` to skip |

Prompts are fully overridable via `.env` or `prompts/system.txt` file — no code changes required.
All runtime config is live-reloadable via Web UI `/config` tab.

---

## 4. Architecture

### High-level flow

```
[Sources] ──▶ idea_candidates ──▶ [HITL review] ──▶ ideas (draft)
                                                         │
                                                    idea_gen ◀── Voice Profile (few-shot)
                                                         │
                                               ══ HITL GATE ══
                                               script review + approve
                                                         │
                                tts → bgm_mix → scenes → clips → render
                                                         │
                                         thumbnail → qa_check → upload_yt
```

### State machine (SQLite)
```
draft → script_pending → ready → rendering → done
                                           → failed (retryable per step)
```

### Folder structure

```
shorts-factory/
├── shorts/
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py           # LLMProvider interface
│   │   │   ├── openrouter.py     # default
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   ├── gemini.py
│   │   │   ├── ollama.py
│   │   │   ├── claude_cli.py     # subprocess: claude CLI sub
│   │   │   ├── gemini_cli.py     # subprocess: gemini CLI sub
│   │   │   └── codex_cli.py      # subprocess: codex CLI sub
│   │   ├── tts/
│   │   │   ├── base.py
│   │   │   ├── edge_tts.py       # default (free)
│   │   │   ├── elevenlabs.py
│   │   │   └── openai_tts.py
│   │   └── clips/
│   │       ├── base.py           # ClipsProvider interface (extensible for AI gen v2)
│   │       ├── pexels.py         # default
│   │       ├── pixabay.py
│   │       └── local.py          # local folder
│   ├── nodes/                    # pipeline steps
│   │   ├── idea_gen.py
│   │   ├── tts.py
│   │   ├── bgm_mix.py
│   │   ├── scenes.py
│   │   ├── clips.py
│   │   ├── render.py
│   │   ├── thumbnail.py
│   │   ├── qa_check.py
│   │   └── upload_yt.py
│   ├── sources/                  # idea fetchers
│   │   ├── google_trends.py      # default (free, pytrends)
│   │   ├── llm_trends.py         # default (uses LLM provider)
│   │   ├── reddit.py
│   │   ├── youtube.py
│   │   ├── rss.py
│   │   └── google_discover.py    # [experimental]
│   ├── voice/                    # Author Voice system (new)
│   │   ├── profile.py            # build + query voice profile
│   │   └── examples.py           # seed + approved script store
│   ├── web/                      # FastAPI — 4 tabs
│   ├── pipeline.py               # orchestrator, idempotent
│   ├── db.py                     # SQLite schema + queries
│   ├── config.py                 # config_store, live reload
│   └── cli.py                    # `shorts` CLI entrypoint
├── prompts/
│   └── system.txt.example        # override default system prompt here
├── data/                         # gitignored
├── secrets/                      # gitignored
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 5. Provider Layer

### LLMProvider interface
```python
class LLMProvider:
    def complete(self, system: str, user: str, **kwargs) -> str: ...
    def name(self) -> str: ...
```

### CLI subscription adapters
```python
class ClaudeCLIProvider(LLMProvider):
    """Uses Claude Pro subscription via `claude` CLI subprocess.
    Requires: claude CLI installed and authenticated.
    """
    def complete(self, system: str, user: str, **kwargs) -> str:
        result = subprocess.run(
            ["claude", "-p", user, "--system", system,
             "--output-format", "json"],
            capture_output=True, text=True, timeout=120
        )
        return parse_claude_json(result.stdout)
```

Same pattern for `GeminiCLIProvider` and `CodexCLIProvider`.

### ClipsProvider interface (designed for v2 AI gen extensibility)
```python
class ClipsProvider:
    def search(self, query: str, count: int) -> list[ClipResult]: ...
    def download(self, clip: ClipResult, out_dir: Path) -> Path: ...
    def source_type(self) -> str: ...  # "stock" | "ai-generated"
```

---

## 6. Author Voice System

### Tables (SQLite)
- `voice_examples` — seed scripts added manually
- `approved_scripts` — every user-approved script + edit delta, with timestamp weight
- `voice_notes` — per-idea style notes

### CLI
```bash
shorts voice seed --file sample.txt    # add seed script
shorts voice seed --text "Hôm nay..."
shorts voice list                      # view profile summary
shorts voice stats                     # example count, avg edit delta
shorts voice reset                     # clear profile
```

### Injection into idea_gen
```python
examples = voice_profile.get_top_examples(n=3)
system_prompt = BASE_PROMPT + format_few_shot(examples)
```

Weight increases with recency and edit frequency. No fine-tuning required.

---

## 7. Web UI (FastAPI, 4 tabs)

| Tab | Path | Purpose |
|---|---|---|
| Ideas | `/ideas` | Fetch candidates, approve/reject, add manual ideas |
| Pipeline | `/pipeline` | List jobs, step status, retry failed step |
| Voice | `/voice` | Seed scripts, view profile, stats |
| Config | `/config` | Provider settings, live reload, no restart needed |

Not in v1: analytics, user auth, admin panel — those are SaaS v2 scope.

---

## 8. Idea Sources

| Source | Key required | Default? |
|---|---|---|
| Google Trends (`pytrends`) | None | ✅ yes |
| LLM-generated trends | LLM provider | ✅ yes |
| Reddit | `REDDIT_CLIENT_ID` | Optional |
| YouTube | `YOUTUBE_API_KEY` | Optional |
| RSS | Feed URLs in `.env` | Optional |
| Google Discover | None (experimental) | ❌ experimental |

---

## 9. Docker / Onboarding

```bash
# 3-step setup for non-devs:
cp .env.example .env        # fill in API keys
docker compose up           # start
open http://localhost:8765  # use
```

Docker volumes: `data/` (SQLite + sessions), `secrets/` (YouTube OAuth), `data/bgm/` (background music).

---

## 10. v1 Scope (what ships)

- [x] Full pipeline: idea → script → TTS → render → upload
- [x] HITL gate (script review)
- [x] Idempotent pipeline (step-level resume)
- [x] LLM providers: OpenRouter, OpenAI, Anthropic, Gemini, Ollama
- [x] LLM CLI adapters: claude-cli, gemini-cli, codex-cli
- [x] TTS: Edge-TTS (default), ElevenLabs, OpenAI TTS
- [x] Clips: Pexels (default), Pixabay, local folder
- [x] Idea sources: Google Trends, LLM trends, Reddit, YouTube, RSS
- [x] Author Voice system (seed + edit loop + few-shot injection)
- [x] Web UI (4 tabs)
- [x] Docker Compose
- [x] Prompt override via file or .env

## Roadmap (post-v1)

- [ ] AI-generated clips via Gemini CLI → Veo 2/3 (Google AI Pro sub)
- [ ] AI-generated clips via Veo API (pay-per-second)
- [ ] AI-generated clips via Wan 2.6 local (requires powerful GPU)
- [ ] AI-generated clips via Kling AI API, Runway Gen API
- [ ] Multi-channel support (multiple YouTube accounts)
- [ ] Scheduling (auto-publish at optimal time)
- [ ] Analytics tab (YouTube Analytics API)
- [ ] SaaS wrapper (auth, billing, hosted)

---

## 11. What's stripped from youtube-meo (private → public)

The following are intentionally excluded from the public repo:
- All Vietnamese cat channel branding (`purrfectmind`, `Cat Diary` prompts)
- `.claude/`, `.agents/`, `memory/`, `.skills/`, `.superpowers/` (Claude Code internals)
- `*.plugin` files (claude-runtime-rules, meo-channel, meo-morning)
- `conductor/`, `evals/`, `luvmeo-bio/` (channel-specific)
- `secrets/` (OAuth credentials)
- Any hardcoded channel names, voice names, or niche-specific prompts

Default prompts in the public repo are niche-agnostic and language-configurable.
