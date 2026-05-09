# shorts-factory — Design Spec v1.2

**Date:** 2026-05-09
**Status:** Draft — post adversarial review round 2
**Author:** Tuan Khuc + Claude
**Changes from v1.1:** see §13 (rows 10-13)

---

## 1. Positioning

### Tagline
> "Turn any idea into a YouTube Short — bring your own LLM, any language, any niche."

### What it is
`shorts-factory` is an open-source, self-hosted **video production pipeline** that automates YouTube Shorts assembly: idea sourcing → script generation → TTS → video render → YouTube upload.

### What it is NOT (v1)
- Not a SaaS product (that comes later)
- Not a clip-from-existing-video tool (Opus Clip territory)
- Not an AI actor / talking head tool
- **Not a monetization tool.** Output suitability for YouTube Partner Program depends on your edits, original commentary, and adherence to YouTube policies. This tool produces raw assembly only.

### Target users
- **Primary:** Developers who self-host, configure `.env`, run Docker
- **Secondary:** Technical content creators comfortable with Docker

### Origin
Extracted and generalized from `youtube-meo` (private repo — a Vietnamese cat Shorts channel pipeline). The private repo remains as internal reference; this public repo is a clean rewrite.

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
Most repos hardcode one provider and require a separate API key — even if you already pay for Claude Pro or ChatGPT Plus.

`shorts-factory` supports two access modes:
- **API key mode** — OpenRouter (default, 100+ models, 1 key), OpenAI, Anthropic, Gemini, Ollama local
- **CLI subscription mode** — use your existing subscription via CLI subprocess (zero extra billing):
  - `LLM_PROVIDER=claude-cli` → uses Claude Pro/Max via `claude` CLI (local dev only — see §5.1)
  - `LLM_PROVIDER=codex-cli` → uses ChatGPT Plus/Pro via `codex exec` (officially supported automation path)
  - **Gemini (manual mode)** — no shipped provider; documented bash workflow only (§5.2)

### USP 2 — HITL gate (script review before burning resources)
All competing repos run fully automated — no review before TTS + render. `shorts-factory` pauses at `script_pending` state, lets the user read and approve, then continues. Prevents wasted renders on bad scripts.

### USP 3 — Idempotent pipeline (resume from any step)
Each pipeline step logs its result in SQLite. Re-running a job skips already-completed steps. Delete a specific output file to force re-run of that step only. State conflict resolution: see §6.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
Most repos use a single fixed system prompt. `shorts-factory` accumulates approved scripts as few-shot examples that get injected into future `idea_gen` calls.

Sources:
- **Seeds:** user-written script samples (`shorts voice seed`)
- **Notes/salting:** per-idea style notes (`shorts add "title" --note "..."`)
- **Approval log:** every user-approved script + edit delta, weighted by recency

This is **not fine-tuning** and **not a learned style model**. It's deterministic few-shot prompt assembly. Quality improvement depends on example quality. No quality metric is shipped in v1; users evaluate output themselves. Future work (§roadmap): A/B harness + edit-delta tracking.

---

## 3. Philosophy

**Free by default, configurable everything.**

| Layer | Free default | Configurable alternatives |
|---|---|---|
| Idea sources | Google Trends + LLM-generated | Reddit, YouTube API, RSS, custom |
| LLM | OpenRouter (user provides key) | OpenAI, Anthropic, Gemini, Ollama, claude-cli, codex-cli |
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
                          ┌──── idea_gen ◀── Few-shot examples (approved scripts)
                          │      OR
                          └──── --script-file (manual injection, e.g. Gemini bash)
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
│   │   │   ├── gemini.py         # API key only
│   │   │   ├── ollama.py
│   │   │   ├── claude_cli.py     # subprocess: claude CLI (local-only)
│   │   │   └── codex_cli.py      # subprocess: codex exec
│   │   ├── tts/
│   │   │   ├── base.py
│   │   │   ├── edge_tts.py       # default (free)
│   │   │   ├── elevenlabs.py
│   │   │   └── openai_tts.py
│   │   └── clips/
│   │       ├── base.py           # ClipsProvider interface (extensible for AI gen v2)
│   │       ├── pexels.py         # default
│   │       ├── pixabay.py
│   │       └── local.py
│   ├── nodes/                    # pipeline steps
│   │   ├── idea_gen.py           # supports --script-file bypass
│   │   ├── tts.py
│   │   ├── bgm_mix.py
│   │   ├── scenes.py
│   │   ├── clips.py
│   │   ├── render.py
│   │   ├── thumbnail.py
│   │   ├── qa_check.py
│   │   └── upload_yt.py
│   ├── sources/
│   │   ├── google_trends.py
│   │   ├── llm_trends.py
│   │   ├── reddit.py
│   │   ├── youtube.py
│   │   ├── rss.py
│   │   └── google_discover.py    # [experimental]
│   ├── voice/                    # few-shot example store
│   │   ├── examples.py           # seed + approved script storage
│   │   └── injector.py           # format examples into system prompt
│   ├── web/                      # FastAPI — 4 tabs
│   ├── pipeline.py               # orchestrator, idempotent
│   ├── db.py                     # SQLite schema + queries
│   ├── config.py
│   └── cli.py
├── prompts/
│   └── system.txt.example
├── docs/
│   ├── gemini-manual-mode.md     # bash snippet for Gemini users
│   └── cli-providers-tos.md      # ToS notes for claude-cli / codex-cli
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

### 5.1 CLI subscription adapters — ToS-aware design

Two CLI providers shipped: `claude-cli` and `codex-cli`. Each has different ToS surface; users must verify current vendor terms before use. Disclaimer printed at first run.

**`claude_cli.py`** — Claude Pro/Max via `claude` CLI
- Documented use: **local development only** (your own Mac/Linux desktop)
- Not recommended for: VPS, server, always-on deployments. Per Anthropic's stance, subscription auth on remote servers is a gray area.
- Anthropic explicitly permits scripted local use of `claude` CLI as an intended deployment pattern.

```python
class ClaudeCLIProvider(LLMProvider):
    """Claude Pro/Max via `claude` CLI subprocess. Local desktop only.
    Requires: claude CLI installed and authenticated (`claude /login`).
    See docs/cli-providers-tos.md before deploying.
    """
    def complete(self, system: str, user: str, **kwargs) -> str:
        result = subprocess.run(
            ["claude", "-p", user, "--system-prompt", system,
             "--output-format", "json"],
            capture_output=True, text=True, timeout=120
        )
        return parse_claude_json(result.stdout)
```

**`codex_cli.py`** — ChatGPT Plus/Pro via `codex exec`
- OpenAI explicitly designs `codex exec` as the automation entry point.
- Documented use: scripted automation OK per OpenAI docs.
- Authentication: user runs `codex login` once before pipeline start.

```python
class CodexCLIProvider(LLMProvider):
    """ChatGPT Plus/Pro via `codex exec` subprocess.
    OpenAI documents codex exec as the supported automation path.
    Requires: codex CLI installed and signed in (`codex login`).
    """
    def complete(self, system: str, user: str, **kwargs) -> str:
        result = subprocess.run(
            ["codex", "exec", "--json", f"{system}\n\n{user}"],
            capture_output=True, text=True, timeout=120
        )
        return parse_codex_json(result.stdout)
```

### 5.2 Gemini — manual mode (no shipped provider)

Per Gemini CLI ToS, third-party software wrapping `gemini` CLI's OAuth is prohibited. `shorts-factory` does **not** ship a Gemini CLI provider.

If you want to use Gemini AI Pro subscription for script generation, generate the script manually and inject via `--script-file`:

**macOS / Linux (bash) — file-based input (safe with multi-line/quoted prompts):**
```bash
# Combine system + user prompt into one file
cat prompts/system.txt > /tmp/gemini-prompt.txt
echo -e "\n\nIdea: Cats falling off shelves" >> /tmp/gemini-prompt.txt

# Single invocation, your terminal action
gemini -p "$(cat /tmp/gemini-prompt.txt)" > data/scripts/idea-123.txt
```

**Windows (PowerShell):**
```powershell
$prompt = (Get-Content prompts/system.txt -Raw) + "`n`nIdea: Cats falling off shelves"
$prompt | Set-Content -NoNewline /tmp/gemini-prompt.txt
gemini -p (Get-Content /tmp/gemini-prompt.txt -Raw) | Set-Content data/scripts/idea-123.txt
```

**Why file-based:** inline `$(cat ...)` breaks if `system.txt` contains quotes, backticks, `$`, or newlines that the shell interprets. File staging avoids shell-injection edge cases.

Then inject into pipeline:
```bash
shorts run idea-123 --script-file data/scripts/idea-123.txt
```

This bypasses `idea_gen` entirely. Pipeline picks up at `script_pending` for HITL review.

For API-based Gemini (no ToS concern), use the shipped `gemini.py` provider with `GEMINI_API_KEY` from Google AI Studio.

### 5.3 Provider availability detection

**Two-tier verify:**

1. **Static check** (cheap, no token cost) — runs at `__init__`:
   - CLI: `shutil.which("claude")` exists
   - API key: env var present + format valid
2. **Live ping** (costs 1 minimal call) — runs on demand, result cached

**Cache:** `data/.cache/provider-status.json`, TTL 1h. Live ping skipped if cached `ok` exists. Manual force: `shorts provider verify --force` or `/config` tab "Re-test" button.

```python
class ClaudeCLIProvider(LLMProvider):
    def __init__(self):
        self._static_check()      # cheap

    def _static_check(self):
        if not shutil.which("claude"):
            raise ProviderUnavailable(
                code="cli_not_installed",
                message="claude CLI not installed.",
                install_url="https://docs.claude.com/en/docs/claude-code",
                fallback="Set LLM_PROVIDER=openrouter in .env"
            )

    def verify_live(self) -> VerifyResult:
        """1-token ping. Cached. Caller decides when to invoke."""
        cached = cache.get("claude-cli", ttl=3600)
        if cached: return cached
        result = subprocess.run(
            ["claude", "-p", "ok", "--output-format", "json"],
            capture_output=True, timeout=10
        )
        # cache + return
```

Same pattern for `CodexCLIProvider`, `OllamaProvider`, and API-key providers.

**`OllamaProvider` extras:** static check = `shutil.which("ollama")`; live ping = `ollama list` to confirm daemon running AND target model is pulled. If model missing → `ProviderUnavailable(code="model_not_pulled", message="Run: ollama pull <model>")`. Default model `llama3.2:3b`, configurable via `OLLAMA_MODEL` in `.env`.

**Token-expiry handling:** `complete()` catches auth errors → raises `ProviderAuthExpired` → Web UI surfaces a banner: "Re-login required: run `claude /login`". Pipeline pauses job at current step (idempotent — resumes after re-login).

**First-run flow (Web UI, not CLI):**

`docker compose up` with empty `.env` → app starts in **setup mode**. Browser opens at `http://localhost:8765/setup`:

```
Welcome to shorts-factory.
Pick a provider:
  ● OpenRouter (recommended — 1 API key, 100+ models, free tier)
  ○ OpenAI / Anthropic / Gemini (separate API key)
  ○ Ollama (local, free)
  ○ claude-cli (Claude Pro/Max — requires CLI install + native run)
  ○ codex-cli (ChatGPT Plus/Pro — requires CLI install + native run)
```

CLI options grayed out + tooltip "Docker not supported — see docs/cli-providers-setup.md" if running in container.

After selection, app runs `_static_check()` + `verify_live()`. On fail → in-page error with install link + fallback button. App refuses to leave `/setup` until provider verifies.

**CLI auth out-of-band flow** (when user picks `claude-cli` / `codex-cli`):

1. Static check pass (binary found) → live ping → fails with "not authenticated"
2. UI shows:
   ```
   ⚠ claude CLI installed but not logged in.

   This step happens outside the browser. Open a terminal on
   THIS machine (host, not container) and run:

       claude /login

   When done, click the button below.
   ```
3. "I've logged in — retry" button → re-runs `verify_live()` (cache invalidated)
4. If fail again → same screen + troubleshoot link

This applies to native install (Pattern A). Pattern B users see additional note: "ensure `~/.claude` is mounted RW into the container."

**`ProviderUnavailable` handling app-wide:** any pipeline call that hits this → caught by orchestrator → job marked `blocked` (not `failed`), Web UI banner redirects to `/setup`.

**Status badges in `/config`:**
- 🟢 verified (cached, <1h)
- 🟡 not verified (never tested)
- 🔴 verify failed → "Setup guide" link
- ⚪ static-only (CLI installed, never pinged)

### 5.4 ClipsProvider interface (designed for v2 AI gen extensibility)
```python
class ClipsProvider:
    def search(self, query: str, count: int) -> list[ClipResult]: ...
    def download(self, clip: ClipResult, out_dir: Path) -> Path: ...
    def source_type(self) -> str: ...  # "stock" | "ai-generated"
```

---

### 5.5 Platform support — see §10.2

Consolidated platform matrix and shell snippets are in §10.2. CLI providers require special platform handling per OS — read §10 before deploying.

---

## 6. Idempotent pipeline — state resolution rule

**SQLite is source of truth for step status. Filesystem is artifact storage.**

Step lifecycle:
1. Step starts → DB row created with `status=running`
2. Step writes output file → DB row updated to `status=done` with `output_path`
3. Step fails → DB row updated to `status=failed` with error

Resolution table when re-running a job:

| DB status | Output file exists? | Action |
|---|---|---|
| `done` | yes | Skip step, use existing file |
| `done` | no (user deleted) | Re-run step (DB → `running`) |
| `running` | any | Treat as crashed, re-run step |
| `failed` | any | Re-run step |
| `blocked` | any | Provider unavailable; resume after `/setup` |
| (no row) | any | Run step fresh |

**DB missing/deleted:** all jobs lost. Pipeline starts fresh on next run. Recommendation: nightly backup of `data/shorts.db` to `data/backups/`. Roadmap: built-in backup rotation.

**Force re-run a specific step:** delete the DB row. CLI helper: `shorts step reset <job_id> <step_name>`.

**Subprocess timeout** (CLI providers): default 120s, configurable via `LLM_TIMEOUT_SEC` in `.env`. Long Claude Code tasks may need 300s+.

---

## 7. Few-shot Voice System

### Tables (SQLite)
- `voice_examples` — seed scripts added manually
- `approved_scripts` — every user-approved script + edit delta + timestamp
- `voice_notes` — per-idea style notes

### CLI
```bash
shorts voice seed --file sample.txt    # add seed script
shorts voice seed --text "Hôm nay..."
shorts voice list                      # view profile summary
shorts voice stats                     # example count, avg edit delta
shorts voice reset                     # clear store
```

### Injection into idea_gen
```python
examples = voice_store.get_top_examples(n=3, weight_by="recency")
system_prompt = BASE_PROMPT + format_few_shot(examples)
```

**No quality metric shipped in v1.** Selection is rule-based (recency × edit-magnitude). Users judge output quality themselves.

### Roadmap (not v1)
- Edit-delta scoring across approved scripts
- A/B harness comparing few-shot vs zero-shot output
- Optional embedding-based example selection

---

## 8. Web UI (FastAPI, 4 tabs)

| Tab | Path | Purpose |
|---|---|---|
| Ideas | `/ideas` | Fetch candidates, approve/reject, add manual ideas, **inject manual script** |
| Pipeline | `/pipeline` | List jobs, step status, retry failed step, reset step |
| Voice | `/voice` | Seed scripts, view examples, stats |
| Config | `/config` | Provider settings, live reload, no restart needed |

**Manual script injection (Ideas tab):** "Inject Manual Script" button opens dialog with:
- Idea title field (required)
- Script body — paste textarea OR drag-drop `.txt` file
- Submit → creates job in `script_pending` state, bypassing `idea_gen`
- Equivalent CLI: `shorts run <id> --script-file <path>`

This is the primary flow for Gemini manual mode (§5.2) and any other external script source.

Pipeline tab includes a "Run pipeline" button per job — user-initiated invocation.

Setup tab (`/setup`) appears only when no provider is configured (see §5.3); hidden once setup completes.

Not in v1: analytics, user auth, admin panel, A/B test harness.

---

## 9. Idea Sources

| Source | Key required | Default? |
|---|---|---|
| Google Trends (`pytrends`) | None | ✅ yes |
| LLM-generated trends | LLM provider | ✅ yes |
| Reddit | `REDDIT_CLIENT_ID` | Optional |
| YouTube | `YOUTUBE_API_KEY` | Optional |
| RSS | Feed URLs in `.env` | Optional |
| Google Discover | None (experimental) | ❌ experimental |

---

## 10. Docker / Onboarding

```bash
# 3-step setup (API-key mode):
cp .env.example .env        # fill in API keys
docker compose up           # start
open http://localhost:8765  # use
```

Docker volumes: `data/` (SQLite + sessions + scripts + cache), `secrets/` (YouTube OAuth), `data/bgm/` (background music).

### 10.1 CLI providers + Docker — important

**`claude-cli` and `codex-cli` require interactive OAuth login** (browser popup, paste token). Docker containers have no browser and no user terminal — `claude /login` / `codex login` cannot run inside the container.

**Two supported patterns:**

**Pattern A (recommended): Native Python install, no Docker.**
```bash
# macOS / Linux / WSL2:
git clone <repo> && cd shorts-factory
python -m venv .venv && source .venv/bin/activate
pip install -e .
# install + login CLI on host first:
claude /login    # or: codex login
shorts serve     # starts FastAPI on :8765
```

**Pattern B (advanced): Docker + mounted host credentials.**

User runs `claude /login` on the host once. Then mounts the credential dir read-write into the container:

```yaml
# docker-compose.cli.yml
services:
  app:
    volumes:
      - ~/.claude:/root/.claude:rw       # claude-cli credentials
      - ~/.codex:/root/.codex:rw         # codex-cli credentials
      - /usr/local/bin/claude:/usr/local/bin/claude:ro  # Linux/Mac binary
```

Caveats:
- Path layout differs per OS (Linux: `~/.claude`, macOS: same, Windows: `%USERPROFILE%\.claude`)
- Token refresh writes back to mounted dir — read-write required
- Re-login still happens on host, not container
- Windows: bind-mount of host `.exe`/`.cmd` from PowerShell paths into Linux container = broken. **Use Pattern A on Windows.**

⚠️ **Security note:** mounting `~/.claude` into the container means the container has full account access via your OAuth tokens. If the image or any dependency is compromised, attacker gets your subscription tokens. Pattern B is suitable for local dev only — never on shared hosts, never with untrusted images, never on public-facing servers.

### 10.2 Platform support matrix (consolidated)

| Mode | macOS | Linux | Windows native | WSL2 |
|---|---|---|---|---|
| API key (Docker) | ✅ | ✅ | ✅ | ✅ |
| API key (native Python) | ✅ | ✅ | ✅ | ✅ |
| `claude-cli` native | ✅ | ✅ | ✅ | ✅ |
| `codex-cli` native | ✅ | ✅ | ✅ (PowerShell + Windows sandbox) | ✅ |
| `claude-cli` + Docker (Pattern B) | ⚠ works | ⚠ works | ❌ broken | ⚠ works |
| `codex-cli` + Docker (Pattern B) | ⚠ works | ⚠ works | ❌ broken | ⚠ works |

**Recommendation for Windows users:** WSL2 + native Python venv. Docker Desktop on Windows + CLI providers = pain. Skip Docker if using CLI mode.

**Subprocess portability:** `shutil.which("claude")` resolves `.exe`/`.cmd`/`.bat` on Windows automatically. No code branching.

---

## 11. v1 Scope

- [x] Full pipeline: idea → script → TTS → render → upload
- [x] HITL gate (script review)
- [x] Idempotent pipeline (DB-authoritative, step-level resume)
- [x] LLM providers (API key): OpenRouter, OpenAI, Anthropic, Gemini, Ollama
- [x] LLM CLI adapters: claude-cli (local-only), codex-cli
- [x] Gemini manual mode docs + `--script-file` flag
- [x] TTS: Edge-TTS (default), ElevenLabs, OpenAI TTS
- [x] Clips: Pexels (default), Pixabay, local folder
- [x] Idea sources: Google Trends, LLM trends, Reddit, YouTube, RSS
- [x] Few-shot voice injection (seed + approved scripts)
- [x] Web UI (4 tabs)
- [x] Docker Compose
- [x] Prompt override via file or .env
- [x] ToS disclaimer + docs for CLI providers

## Roadmap (post-v1)

- [ ] Quality metrics for voice system (edit-delta tracking, A/B harness)
- [ ] AI-generated clips: Veo API, Wan 2.6 local, Kling, Runway
- [ ] Multi-channel support
- [ ] Scheduling
- [ ] Analytics tab
- [ ] SaaS wrapper

---

## 12. What's stripped from youtube-meo (private → public)

Excluded:
- Vietnamese cat channel branding (`purrfectmind`, `Cat Diary` prompts)
- `.claude/`, `.agents/`, `memory/`, `.skills/`, `.superpowers/`
- `*.plugin` files
- `conductor/`, `evals/`, `luvmeo-bio/`
- `secrets/`
- Any hardcoded channel names, voice names, niche prompts

Default prompts are niche-agnostic and language-configurable.

---

## 13. Changes from v1.0 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 1 | §1 | Added "not a monetization tool" disclaimer | YouTube 2026 policy flags AI+stock+TTS combo as demonetization risk |
| 2 | §2 USP1 | Dropped `gemini-cli` adapter; added `codex-cli` framing | Gemini ToS prohibits 3rd-party wrappers; OpenAI explicitly endorses `codex exec` |
| 3 | §2 USP4 | Renamed "Author Voice" → "Few-shot voice injection"; dropped "learns your style" | Original claim unmetricable, sounded like fine-tuning |
| 4 | §5.1 | Per-provider ToS notes; `claude-cli` labeled local-only | Anthropic ToS distinguishes local vs VPS |
| 5 | §5.2 | Gemini manual mode via `--script-file` + file-based bash (safe with multi-line/quoted prompts) | User runs `gemini -p` themselves; inline `$(cat)` breaks on quotes/newlines |
| 6 | §6 | DB-vs-filesystem state resolution rule + DB-missing recovery + subprocess timeout config | v1.0 idempotent claim lacked spec for conflict cases |
| 7 | §10.1 | CLI providers: native install primary path; Pattern B (mounted credentials) for advanced | Interactive OAuth `claude /login` impossible inside container |
| 8 | §5.3 | Two-tier verify (static check at init, live ping cached 1h); Web UI `/setup` flow replaces CLI wizard; `ProviderAuthExpired` handling | Token-burning per-init; CLI wizard conflicts with Docker-first onboarding; tokens expire mid-pipeline |
| 9 | §10.2 | Win/Mac/Linux support matrix + dual-shell docs | Windows users likely majority; Docker+CLI on Win is broken |
| 10 | §10.1 | Pattern B security warning (token theft risk) | Mounted `~/.claude` = full account access if container compromised |
| 11 | §5.3 | CLI auth out-of-band flow with "I've logged in — retry" button | User in browser can't run `claude /login`; explicit host-terminal instruction needed |
| 12 | §5.3 | Ollama: model-pulled check + default `llama3.2:3b` config | `ollama list` alone doesn't catch missing model; cryptic 404 otherwise |
| 13 | §8 | "Inject Manual Script" dialog spec (paste OR drag-drop) | Web UI is primary; manual mode needs UI flow, not just CLI |

---

## 14. Open questions (defer to implementation)

- Docker + host CLI binary pattern: bind-mount `claude` binary, sidecar container, or host-network mode? Pick one in v1.0.0.
- Claude CLI output format: `--output-format json` schema may shift. Pin CLI version in `.env.example` and document upgrade path.
- Codex CLI rate limits with Plus vs Pro: surface in `/config` tab as info text.
- YouTube Data API v3 quota (10k units/day ≈ 6 uploads/day): document in README.