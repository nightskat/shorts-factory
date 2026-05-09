# shorts-factory — Design Spec v1.4

**Date:** 2026-05-09
**Status:** Draft — post adversarial review round 4 (multi-vendor BOM: Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.3:** see §13 (rows 27-33)

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
Each pipeline step logs its result in SQLite. Re-running a job skips already-completed steps. If a step needs to be re-run, use `shorts step reset <job_id> <step>` to invalidate it and downstream dependencies. State conflict resolution: see §6.

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

Prompts are fully overridable via `.env` or `prompts/system.txt` file.

**Configuration Isolation:** To ensure idempotency, the global configuration (from `.env` and UI) is **snapshotted** when a job begins processing. Mid-job changes to `.env` will only affect *new* jobs, preventing non-deterministic resume behavior (§6.1).

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

### State Machine (SQLite)
The orchestrator relies on two distinct state machines to avoid logic collisions:

**1. Job Level (`jobs` table)** - tracks overall progression.
```
draft → pending_script → processing → pending_upload → completed
                                    ↘ failed
```

**2. Step Level (`step_results` table)** - tracks individual node execution.
```
running → done
        ↘ failed
        ↘ blocked (e.g. provider auth expired, requires user action)
```

### Folder structure

```
shorts-factory/
├── shorts/
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── openrouter.py
│   │   │   ├── claude_cli/       # CLI integration moved to adapter module
│   │   │   │   ├── adapter.py    # version detection & routing
│   │   │   │   └── v0_2.py       # contract for 0.2.x CLI versions
│   │   │   └── codex_cli/
│   │   │       ├── adapter.py
│   │   │       └── v1_0.py
│   │   ├── tts/
│   │   └── clips/
│   ├── nodes/
│   ├── sources/
│   ├── voice/
│   ├── web/
│   ├── utils/
│   │   └── shell.py              # OS path translation & subprocess hardening
│   ├── pipeline.py
│   ├── db.py
│   ├── config.py                 # Live reload + Job-level snapshotting
│   └── cli.py
├── prompts/
├── docs/
├── data/
├── secrets/
├── docker-compose.yml
├── docker-compose.cli.yml        # Opt-in Pattern B
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 5. Provider Layer

### 5.1 CLI subscription adapters — Versioned Contracts

Two CLI providers shipped: `claude-cli` and `codex-cli`.
Because CLI output formats and flags (e.g., `--input-format stream-json`) are unstable, direct `subprocess.run` calls are routed through an **adapter layer**. The adapter runs `claude --version`, matches it to a known contract (e.g., `v0_2.py`), and applies the correct parsing logic. Unsupported versions gracefully degrade or request a framework update.

**Subprocess Hardening:**
1. **Never pass prompts via argv** — Use stdin or a permissioned temp file (`0600`).
2. **Environment Allowlist** — Prevent `.env` leak.
3. **Timeout Enforced**.

```python
# Expanded to support Windows & common network setups
SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    "SystemRoot", "TEMP", "TMPDIR", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"
}

def _safe_env() -> dict:
    return {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
```

### 5.2 Gemini — manual mode
Per ToS, no shipped provider. Documented workflow:
```bash
# Combine into temp file (Windows: use $env:TEMP)
{ cat prompts/system.txt; echo; echo "Idea: Cats..." } > /tmp/gemini-prompt.txt
gemini < /tmp/gemini-prompt.txt > data/scripts/idea-123.txt
rm /tmp/gemini-prompt.txt
shorts run idea-123 --script-file data/scripts/idea-123.txt
```

### 5.3 Provider availability detection

**Lazy verification — only the selected provider is checked.**
1. **Static check** (cheap) — runs at first use.
2. **Live ping** (costs 1 minimal call) — runs on demand, result cached.

**Cache:** `data/.cache/provider-status.json`, TTL 1h, **stores only status code + timestamp**.
UI surfaces latency smoothly: the `/config` tab shows a "Verifying..." spinner during the live ping.

---

## 6. Idempotent pipeline — state resolution rule

**SQLite is source of truth for step status. Filesystem is artifact storage.**

### 6.1 Job Snapshotting
To prevent mid-flight changes from breaking hash checks, the orchestrator snapshots relevant `.env` parameters into a `config_snapshot` JSON column in the `jobs` table when moving out of `draft`. All steps within that job read from the snapshot, not live config.

### 6.2 Step record schema
```sql
CREATE TABLE step_results (
    job_id TEXT,
    step_name TEXT,
    status TEXT,         -- running|done|failed|blocked
    input_hash TEXT,     -- sha256 of inputs (uses job config_snapshot)
    provider_id TEXT,
    output_path TEXT,
    output_checksum TEXT,
    lease_owner TEXT,     -- PID@hostname
    lease_heartbeat_at,
    attempt_id TEXT,
    PRIMARY KEY (job_id, step_name)
);
```

### 6.3 Skip rule (input-hash gated)
Step skips only if **all match**: `status=done` AND `output_path` exists AND `output_checksum` matches AND `input_hash` matches. Mismatch → Re-run + cascade invalidate downstream.
Force re-run command: `shorts step reset <job_id> <step>`.

### 6.4 YouTube upload — duplicate prevention
`upload_yt` is the riskiest step.
1. Generate deterministic `idempotency_key` (`job_id`).
2. Write to `youtube_upload` table with `status=running` and `resumable_session_url`.
3. **Hidden Footer:** Append `\n\n[sf-id: {idempotency_key}]` to the YouTube video description.
4. On crash mid-upload:
   - Try resuming `resumable_session_url`.
   - If expired, search user's recent uploads (via Data API) for the `[sf-id: xyz]` string in the description.
   - If found, mark `done`. If not, start new upload.

---

## 7. Few-shot Voice System
(Remains identical to v1.3)

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security defaults & Auth Flow
The Web UI handles provider credentials and local file system access.
- **Default bind:** `127.0.0.1:8765` (loopback only).
- **Authentication Flow:**
  1. On first boot, a strong `auth.token` is generated and logged to the console.
  2. If the user accesses the UI, they are redirected to a `/login` page.
  3. User enters the token. The backend verifies it and sets an `HttpOnly`, `SameSite=Strict` session cookie.
  4. All API mutating endpoints check the session cookie AND require a standard CSRF header.
- **CSP & Sanitization:** Strict Content Security Policy. Script previews are sanitized via `bleach` (no `<script>`, `<iframe>`, `javascript:`).

### 8.2 Tabs
- `/ideas`
- `/pipeline` (includes pre-upload gate)
- `/voice`
- `/config`

### 8.3 Pre-upload HITL gate
After `qa_check`, job status becomes `pending_upload`. User must explicitly confirm ToS and privacy settings in the UI before it proceeds to `completed`.

---

## 10. Docker / Onboarding

**Pattern A (recommended): Native Python install, no Docker.** (Required for CLI providers).
**Pattern B (UNSAFE — developer use only): Docker + mounted host credentials.**
Opt-in via `docker-compose.cli.yml`. Clearly documented as Account-Takeover risk.

*Windows Users:* Use WSL2 + native Python.

---

## 13. Changes from v1.3 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 27 | §4 | Unify state machine into distinct Job and Step levels | Prevent implementation logic traps with overlapping statuses |
| 28 | §6.5 | Standardize YouTube duplicate prevention via hidden `[sf-id: xyz]` footer tag | "Search metadata" was ambiguous; specific footer string enables deterministic regex search via API |
| 29 | §8.1 | Redesign UI Auth with formal `/login` page and `SameSite` cookies | Clarify how LAN users authenticate; separate browser auth from API header auth |
| 30 | §3, §6.1 | Implement Job-level Config Snapshotting | Ensure mid-job `.env` changes don't cause non-deterministic idempotency hash failures |
| 31 | §5.1 | Move CLI commands to version-pinned `adapters/` layer | Protect against schema drift in unstable external CLIs |
| 32 | §5.1 | Expand `SAFE_ENV_KEYS` to include OS-essential vars | Prevent subprocess breakage on Windows (`SystemRoot`, `TEMP`) and network proxies |
| 33 | §2, §6 | Standardize force-rerun instruction to `shorts step reset` | Resolve conflicting documentation regarding deleting output files vs deleting DB rows |
