# shorts-factory — Design Spec v1.3

**Date:** 2026-05-09
**Status:** Draft — post adversarial review round 3 (multi-vendor BOM: Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.2:** see §13 (rows 14-26)

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
- **API key mode** — OpenRouter (default, 100+ models, 1 key), OpenAI, Anthropic, Gemini, Ollama local. **Recommended for compliance and reliability.**
- **CLI subscription mode** (experimental, user-risk):
  - `LLM_PROVIDER=claude-cli` → uses Claude Pro/Max via `claude` CLI (local dev only — see §5.1)
  - `LLM_PROVIDER=codex-cli` → uses ChatGPT Plus/Pro via `codex exec` (non-interactive CLI path exists; **user must verify current ChatGPT/Codex plan terms permit this workload** — Plus/Pro subscriptions may rate-limit, charge credits, or flag pipeline-style automation)
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

| Layer | Default | Configurable alternatives |
|---|---|---|
| Idea sources | Google Trends + LLM-generated | Reddit, YouTube API, RSS, custom |
| LLM | OpenRouter (user provides key) | OpenAI, Anthropic, Gemini, Ollama, claude-cli, codex-cli |
| TTS | Edge-TTS (unofficial free, opt-in) | ElevenLabs, OpenAI TTS, local Coqui — production-recommended |
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
                                               ══ HITL GATE 1 ══
                                               script review + approve
                                                         │
                                tts → bgm_mix → scenes → clips → render
                                                         │
                                         thumbnail → qa_check
                                                         │
                                               ══ HITL GATE 2 ══
                                               pre-upload: copyright/privacy/ToS confirmation; default --no-publish
                                                         │
                                                   upload_yt
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

**Security rules for all CLI subprocess calls:**
1. **Never pass prompts via argv** — argv is visible in `ps`, `/proc`, OS diagnostics, and crash dumps. Use stdin or a permissioned temp file (mode 0600, deleted after).
2. **Environment allowlist** — explicit env passed to subprocess; never inherit full env (would leak `.env` API keys to CLI process).
3. **Timeout enforced** — kill subprocess on timeout; mark step failed.
4. **Validate exit code** — nonzero = failed; never silently retry.

```python
SAFE_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM"}

def _safe_env() -> dict:
    return {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}

class ClaudeCLIProvider(LLMProvider):
    """Claude Pro/Max via `claude` CLI subprocess. Local desktop only.
    Requires: claude CLI installed and authenticated (`claude /login`).
    See docs/cli-providers-tos.md before deploying.
    """
    def complete(self, system: str, user: str, **kwargs) -> str:
        # Stdin input — no argv leakage
        payload = json.dumps({"system": system, "user": user})
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--input-format", "stream-json"],
            input=payload,
            capture_output=True, text=True,
            timeout=int(os.getenv("LLM_TIMEOUT_SEC", "120")),
            env=_safe_env(),
        )
        if result.returncode != 0:
            raise ProviderError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
        return parse_claude_json(result.stdout)
```

**`claude_cli.py`** — Claude Pro/Max via `claude` CLI
- Documented use: **local development only** (your own Mac/Linux desktop)
- Not recommended for: VPS, server, always-on deployments
- Anthropic explicitly permits scripted local use of `claude` CLI as an intended deployment pattern

**`codex_cli.py`** — ChatGPT Plus/Pro via `codex exec`
- `codex exec` is documented as a non-interactive CLI mode by OpenAI
- **User responsibility:** verify that current ChatGPT Plus/Pro plan terms permit this workload. Pipeline-style automation may consume credits, hit rate limits, or be flagged by OpenAI as suspicious activity. API-key mode is the compliance-safe default for sustained automation.
- Authentication: user runs `codex login` once before pipeline start
- Same stdin + env-allowlist pattern as `ClaudeCLIProvider`

### 5.2 Gemini — manual mode (no shipped provider)

Per Gemini CLI ToS, third-party software wrapping `gemini` CLI's OAuth is prohibited. `shorts-factory` does **not** ship a Gemini CLI provider.

If you want to use Gemini AI Pro subscription for script generation, generate the script manually and inject via `--script-file`:

**macOS / Linux (bash) — stdin input (avoids argv length limits + process-list leakage):**
```bash
# Combine system + user prompt into one file
{
  cat prompts/system.txt
  echo
  echo "Idea: Cats falling off shelves"
} > /tmp/gemini-prompt.txt

# Pipe via stdin if supported, else file argument
gemini < /tmp/gemini-prompt.txt > data/scripts/idea-123.txt

# (If your gemini CLI version requires -p, fall back to: gemini -p "$(cat /tmp/gemini-prompt.txt)")
rm /tmp/gemini-prompt.txt   # don't leave prompts in /tmp
```

**Windows (PowerShell) — uses `$env:TEMP` not `/tmp`:**
```powershell
$promptFile = Join-Path $env:TEMP "gemini-prompt.txt"
$prompt = (Get-Content prompts/system.txt -Raw) + "`n`nIdea: Cats falling off shelves"
$prompt | Set-Content -NoNewline $promptFile

Get-Content $promptFile -Raw | gemini > data/scripts/idea-123.txt
Remove-Item $promptFile
```

**Privacy note:** if your `gemini` CLI version doesn't support stdin, the fallback `gemini -p "$(cat ...)"` exposes the prompt in process listings briefly. Acceptable for local use; not for shared/multi-user hosts.

Then inject into pipeline:
```bash
shorts run idea-123 --script-file data/scripts/idea-123.txt
```

This bypasses `idea_gen` entirely. Pipeline picks up at `script_pending` for HITL review.

For API-based Gemini (no ToS concern), use the shipped `gemini.py` provider with `GEMINI_API_KEY` from Google AI Studio.

### 5.3 Provider availability detection

**Lazy verification — only the selected provider is checked.** App boot does not init all providers. `_static_check()` runs at first use of the active provider. This prevents the app from refusing to start because user doesn't have `claude` CLI installed when they only want OpenAI.

**Two-tier verify:**

1. **Static check** (cheap, no token cost) — runs at first use:
   - CLI: `shutil.which("claude")` exists
   - API key: env var present + format valid
2. **Live ping** (costs 1 minimal call) — runs on demand, result cached

**Cache:** `data/.cache/provider-status.json`, TTL 1h, **stores only status code + timestamp** (no stdout/stderr/provider messages — those may contain prompts or auth fragments). Manual force: `shorts provider verify --force` or `/config` tab "Re-test" button.

**Live ping is opt-in, not implicit at boot.** Triggered by: explicit user click in `/setup` or `/config`, or first pipeline call after provider change. App boot itself does not make network calls.

```python
SAFE_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM"}

class ClaudeCLIProvider(LLMProvider):
    def __init__(self):
        self._verified = False  # lazy

    def _ensure_verified(self):
        if self._verified: return
        self._static_check()
        self._verified = True

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
            ["claude", "-p", "--output-format", "json"],
            input="ok",
            capture_output=True, text=True, timeout=10,
            env={k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ},
        )
        # cache only status code + timestamp; never raw stdout/stderr
```

Same pattern for `CodexCLIProvider`, `OllamaProvider`, and API-key providers.

**`OllamaProvider` extras:** static check = `shutil.which("ollama")`; live ping = `ollama show <model>` (not just `ollama list`) to confirm daemon running AND target model is pulled. If model missing → `ProviderUnavailable(code="model_not_pulled", message="Run: ollama pull <model>")`. Default model `llama3.2:3b`, configurable via `OLLAMA_MODEL` in `.env`.

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

### 6.1 Step record schema
Each step result row stores enough provenance to detect stale outputs:
```sql
CREATE TABLE step_results (
    job_id TEXT,
    step_name TEXT,
    status TEXT,         -- running|done|failed|blocked
    input_hash TEXT,     -- sha256 of all step inputs
    config_hash TEXT,    -- sha256 of step config (model, prompt, params)
    provider_id TEXT,    -- e.g. "openrouter:claude-sonnet-4.6"
    output_path TEXT,
    output_checksum TEXT, -- sha256 of output file
    output_bytes INTEGER,
    started_at,
    finished_at,
    lease_owner TEXT,     -- PID@hostname
    lease_heartbeat_at,   -- updated every 30s
    attempt_id TEXT,      -- UUID per attempt
    PRIMARY KEY (job_id, step_name)
);
```

### 6.2 Skip rule (input-hash gated)
Step skips only if **all match**: `status=done` AND `output_path` exists AND `output_checksum` matches AND `input_hash` matches current input AND `config_hash` matches current config. Any mismatch → re-run step + invalidate all downstream steps (cascade reset their rows).

| State | Action |
|---|---|
| `done` + all hashes match + file OK | Skip |
| `done` + input/config hash differs | Re-run + cascade invalidate downstream |
| `done` + file missing or checksum mismatch | Re-run step |
| `running` + lease alive (heartbeat <2min) | Concurrent run blocked |
| `running` + lease stale (heartbeat >2min) | Treat as crashed, re-run |
| `failed` | Re-run step |
| `blocked` | Provider unavailable; resume after `/setup` |
| (no row) | Run step fresh |

### 6.3 Concurrency — lock/lease
Before running a step, worker acquires lease: writes `lease_owner=PID@host`, `lease_heartbeat_at=now`, `attempt_id=uuid4()`. Heartbeat updates every 30s while running. Stale lease (>2min no heartbeat) → another worker can claim. Two simultaneous "Run" clicks → second one sees live lease → returns "Job already running by PID 1234, attempt abc..." instead of corrupting artifacts.

### 6.4 Atomic writes
Every step writes to `<output_path>.tmp.<attempt_id>`, fsyncs, then renames atomically to `<output_path>`. Partial files never appear at final path. DB row updated only after successful rename + checksum compute.

### 6.5 YouTube upload — duplicate prevention
`upload_yt` is the riskiest step (network I/O + irreversible side effect). Special handling:
1. Before bytes leave the machine, `step_results` row updated with `status=running` + a new `youtube_upload` table row containing:
   - `resumable_session_url` (returned by YouTube Data API resumable upload init)
   - `idempotency_key` (deterministic from `job_id` + `attempt_id`)
2. On crash mid-upload, retry resumes from the same `resumable_session_url` (YouTube supports resumable uploads).
3. If session URL expired → query YouTube Data API for videos with the `idempotency_key` in description metadata before re-uploading. If found, mark step `done` with that video ID. **Never blind-retry.**
4. After upload succeeds, persist `video_id` immediately. Subsequent re-runs skip via the duplicate-detection check.

### 6.6 Misc
**DB missing/deleted:** all jobs lost. Pipeline starts fresh on next run. Recommendation: nightly backup of `data/shorts.db` to `data/backups/`. Roadmap: `shorts doctor` for orphan artifact detection + built-in backup rotation.

**Force re-run a specific step:** delete the DB row. CLI helper: `shorts step reset <job_id> <step_name>` (also cascades downstream invalidation).

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

### 8.1 Security defaults
The Web UI exposes provider credentials, OAuth tokens, manual script injection, and pipeline run buttons. Default config must not allow unauthenticated remote access.

- **Default bind: `127.0.0.1:8765`** (loopback only). Remote access requires explicit `WEB_BIND=0.0.0.0` + auth token configured.
- **Auth token** generated on first boot, stored in `data/auth.token` (mode 0600). Required header: `X-Shorts-Token: <token>` for all non-localhost requests. Token printed once in startup log; user can rotate via `shorts auth rotate`.
- **CSRF protection** on all state-changing endpoints (POST/PUT/DELETE) via per-session token + `SameSite=Strict` cookie.
- **Content Security Policy** headers: `default-src 'self'; script-src 'self'; object-src 'none'`.
- **Secret redaction in UI**: API keys masked as `sk-***...***xyz` in `/config`; never echoed in error messages or logs.
- **Script preview sanitization**: manual scripts stored as plain text only. If preview renders Markdown, sanitize with `bleach` allowlist (no `<script>`, `<iframe>`, `<object>`, no inline `on*` handlers, no `javascript:` URLs).

### 8.2 Tabs

| Tab | Path | Purpose |
|---|---|---|
| Ideas | `/ideas` | Fetch candidates, approve/reject, add manual ideas, **inject manual script** |
| Pipeline | `/pipeline` | List jobs, step status, retry failed step, reset step, **pre-upload gate** |
| Voice | `/voice` | Seed scripts, view examples, stats |
| Config | `/config` | Provider settings, live reload, no restart needed |

### 8.3 Manual script injection (Ideas tab)
"Inject Manual Script" button opens dialog with:
- Idea title field (required)
- Script body — paste textarea OR drag-drop `.txt` file
- Submit → creates job in `script_pending` state, bypassing `idea_gen`
- Equivalent CLI: `shorts run <id> --script-file <path>`
- Body stored as plain text; sanitized on render (see §8.1)

### 8.4 Pre-upload HITL gate (Pipeline tab)
After `qa_check` completes, jobs enter `upload_pending` state (not auto-uploaded). Pipeline tab shows a confirmation card per job:

```
☐ I confirm this video does not infringe copyright (music, footage, IP)
☐ I confirm no minors / private individuals are identifiably featured without consent
☐ I have read YouTube's monetization & community guidelines
☐ I have set the correct privacy level: [Public / Unlisted / Private ▼]

[Cancel] [Confirm and Upload]
```

Default privacy on first run = `Private`. User must explicitly switch + tick all boxes to enable upload. Confirmation logged to DB with timestamp + user agent.

`--no-publish` flag (CLI) skips the upload step entirely — produces final video file but never calls YouTube API. Recommended for first runs.

Pipeline "Run pipeline" button is user-initiated invocation.

Setup tab (`/setup`) appears only when no provider is configured (see §5.3).

Not in v1: analytics, multi-user auth, admin panel, A/B test harness.

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
docker compose up           # starts on 127.0.0.1:8765
open http://localhost:8765  # use
```

Docker volumes: `data/` (SQLite + sessions + scripts + cache), `secrets/` (YouTube OAuth), `data/bgm/` (background music).

**Default port mapping is loopback only:**
```yaml
ports:
  - "127.0.0.1:8765:8765"    # default — local only
```
To expose on LAN, user must explicitly change to `"0.0.0.0:8765:8765"` AND configure auth token (§8.1).

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
shorts serve     # starts FastAPI on 127.0.0.1:8765
```

**Pattern B (UNSAFE — developer use only): Docker + mounted host credentials.**

⛔ **Pattern B is opt-in via a separate compose file (`docker-compose.cli.yml`) and is NOT enabled by default.**

Mounting `~/.claude` / `~/.codex` into a container means the container has full account access via your OAuth tokens — a compromised dependency, supply-chain attack on a base image, or container escape grants the attacker full access to your subscription account ("Account-Takeover-in-a-Box").

Use Pattern B only if:
- You fully trust every layer of the image (you built it, you audited it)
- You are on a single-user developer machine, never shared, never public-facing
- You accept the risk that token theft = account takeover with no recovery path beyond `claude /logout` + re-login on every device

```yaml
# docker-compose.cli.yml — opt-in, run with:
# docker compose -f docker-compose.yml -f docker-compose.cli.yml up
services:
  app:
    volumes:
      - ~/.claude:/root/.claude:rw       # rw required for token refresh
      - ~/.codex:/root/.codex:rw
      # Binary mount only works if host/container OS+arch match.
      # macOS Mach-O binary mounted into Linux container = does not execute.
      # Linux→Linux only:
      - /usr/local/bin/claude:/usr/local/bin/claude:ro
```

Caveats:
- Path layout differs per OS (Linux: `~/.claude`, macOS: same, Windows: `%USERPROFILE%\.claude`)
- Token refresh writes back to mounted dir — read-write required (read-only mount breaks auto-refresh)
- Re-login still happens on host, not container
- Windows: bind-mount of host `.exe`/`.cmd` from PowerShell paths into Linux container = broken. **Use Pattern A on Windows.**
- macOS host → Linux container: `claude` binary is Mach-O, won't execute under Linux. Either build the CLI inside the image (no auth — defeats the point) or use Pattern A.

### 10.2 Platform support matrix (consolidated)

| Mode | macOS | Linux | Windows native | WSL2 |
|---|---|---|---|---|
| API key (Docker) | ✅ | ✅ | ✅ | ✅ |
| API key (native Python) | ✅ | ✅ | ✅ | ✅ |
| `claude-cli` native | ✅ | ✅ | ✅ | ✅ |
| `codex-cli` native | ✅ | ✅ | ✅ (PowerShell + Windows sandbox) | ✅ |
| `claude-cli` + Docker (Pattern B, UNSAFE) | ⚠ binary mismatch | ⚠ works | ❌ broken | ⚠ works |
| `codex-cli` + Docker (Pattern B, UNSAFE) | ⚠ binary mismatch | ⚠ works | ❌ broken | ⚠ works |

**Recommendation for Windows users:** WSL2 + native Python venv. Docker Desktop on Windows + CLI providers = pain. Skip Docker if using CLI mode.

**Cross-platform shell utility (`shorts/utils/shell.py`):** abstracts path translation (`/tmp` vs `%TEMP%`), shell-specific quoting, and WSL↔Windows host bridge. All subprocess calls go through this module — no inline branching in pipeline code.

**Subprocess portability:** `shutil.which("claude")` resolves `.exe`/`.cmd`/`.bat` on Windows automatically.

---

## 11. v1 Scope

- [x] Full pipeline: idea → script → TTS → render → upload (with pre-upload HITL gate)
- [x] HITL gate 1 (script review) + HITL gate 2 (pre-upload confirmation)
- [x] Idempotent pipeline: input-hash gated, atomic writes, lock/lease, downstream invalidation
- [x] LLM providers (API key): OpenRouter, OpenAI, Anthropic, Gemini, Ollama
- [x] LLM CLI adapters: claude-cli (local-only), codex-cli (experimental, user-risk)
- [x] Gemini manual mode docs + `--script-file` flag
- [x] TTS: Edge-TTS (unofficial free, opt-in), ElevenLabs, OpenAI TTS
- [x] Clips: Pexels (default), Pixabay, local folder
- [x] Idea sources: Google Trends, LLM trends, Reddit, YouTube, RSS
- [x] Few-shot voice injection (seed + approved scripts)
- [x] Web UI (4 tabs) with auth token, CSRF, CSP, 127.0.0.1 default bind
- [x] Docker Compose (Pattern A default; Pattern B opt-in via separate compose file)
- [x] Prompt override via file or .env
- [x] ToS disclaimer + docs for CLI providers
- [x] Cross-platform shell utility (`shorts/utils/shell.py`)
- [x] YouTube resumable upload + duplicate-detection

## Roadmap (post-v1)

- [ ] Quality metrics for voice system (edit-delta tracking, A/B harness)
- [ ] AI-generated clips: Veo API, Wan 2.6 local, Kling, Runway
- [ ] Multi-channel support
- [ ] Scheduling
- [ ] Analytics tab
- [ ] `shorts doctor` (orphan artifact detection, DB integrity check, backup rotation)
- [ ] CLI parser contract tests (pinned version fixtures)
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
| 1 | §1 | Added "not a monetization tool" disclaimer | YouTube 2026 policy flags AI+stock+TTS combo |
| 2 | §2 USP1 | Dropped `gemini-cli` adapter; added `codex-cli` framing | Gemini ToS prohibits 3rd-party wrappers |
| 3 | §2 USP4 | Renamed "Author Voice" → "Few-shot voice injection" | Original claim unmetricable |
| 4 | §5.1 | Per-provider ToS notes; `claude-cli` labeled local-only | Anthropic ToS distinguishes local vs VPS |
| 5 | §5.2 | Gemini manual mode via `--script-file` + file-based bash | User runs `gemini -p` themselves |
| 6 | §6 | DB-vs-filesystem state resolution rule | v1.0 idempotent claim lacked spec |
| 7 | §10.1 | CLI providers: native install primary path | Interactive OAuth impossible inside container |
| 8 | §5.3 | Two-tier verify; Web UI `/setup` flow | Token-burning per-init; CLI wizard conflicts |
| 9 | §10.2 | Win/Mac/Linux support matrix + dual-shell docs | Windows users likely majority |
| 10 | §10.1 | Pattern B security warning | Mounted creds = full account access |
| 11 | §5.3 | CLI auth out-of-band flow with retry button | User in browser can't run `claude /login` |
| 12 | §5.3 | Ollama: model-pulled check + default config | `ollama list` doesn't catch missing model |
| 13 | §8 | "Inject Manual Script" dialog spec | Web UI is primary; needs UI flow |
| **14** | **§2 USP1, §5.1** | **Soften codex-cli framing — "experimental, user-risk"** | **Plus/Pro plan terms ambiguous for sustained automation** |
| **15** | **§3, §11** | **Edge-TTS labeled "unofficial free, opt-in"** | **Microsoft service no API key = ToS gray area for production** |
| **16** | **§5.1** | **Subprocess: stdin input + env allowlist + timeout** | **Argv leakage to process listings; env inherits API keys** |
| **17** | **§5.3** | **Lazy verification — only selected provider; cache stores no stdout/stderr** | **Init-time verify of all providers blocks app start; cache leaks auth fragments** |
| **18** | **§6** | **Input/config hash, output checksum, atomic writes, downstream invalidation** | **Stale artifacts when inputs change; partial files on crash** |
| **19** | **§6** | **Lock/lease semantics with PID + heartbeat** | **Concurrent runs corrupt artifacts** |
| **20** | **§6.5** | **YouTube resumable upload + idempotency_key + video_id query before retry** | **Crash mid-upload = duplicate video on naive retry** |
| **21** | **§4, §8.4** | **Pre-upload HITL gate (Gate 2): copyright/privacy/ToS confirmation, default Private** | **Auto-upload after qa_check is irreversible side effect** |
| **22** | **§8.1** | **Web UI: 127.0.0.1 default bind, auth token for non-loopback, CSRF, CSP, secret redaction** | **v1.2 was wide-open proxy on LAN; account-takeover risk** |
| **23** | **§8.3** | **Script preview sanitization (bleach allowlist)** | **Drag-drop script could inject XSS into preview** |
| **24** | **§10** | **Default port mapping `127.0.0.1:8765:8765`; LAN exposure requires explicit opt-in + auth** | **Docker default exposed all interfaces** |
| **25** | **§10.1** | **Pattern B: opt-in via separate compose file, "UNSAFE/dev-only" labeling, macOS Mach-O note** | **Default Pattern B = account-takeover-in-a-box** |
| **26** | **§10.2** | **`shorts/utils/shell.py` for path/quoting abstraction** | **`/tmp` vs `%TEMP%`, WSL↔Win, shell escaping not handled in inline code** |

---

## 14. Open questions (defer to implementation)

- Pattern B credential mount: explore separate auth-only sidecar (no app code, just credential refresh) to limit blast radius if main container compromised.
- Claude CLI output format (`--output-format json`) schema may shift across CLI versions. **v1.0.0 action:** pin tested CLI version range in `.env.example`; add parser contract tests with fixture outputs in `tests/fixtures/cli-outputs/`.
- Codex CLI rate limits with Plus vs Pro: surface in `/config` tab as info text + warn when approaching.
- YouTube Data API v3 quota (10k units/day ≈ 6 uploads/day): document in README; surface "Quota Warning" in `/pipeline` tab when usage >70%.
- pytrends backoff + cache strategy: define rate-limit policy + fallback when Google Trends throttles.
- Live ping cache invalidation: when does cached `verified` go stale beyond TTL? On provider config change? On observed auth failure?
- `shorts doctor` scope: orphan artifact reconciliation, DB integrity check, backup rotation — what auto-fixes are safe vs require user confirmation?
