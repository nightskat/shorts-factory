# shorts-factory — Design Spec v1.5

**Date:** 2026-05-09
**Status:** Draft — post adversarial review round 4 (multi-vendor BOM: Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.4:** see §13 (rows 34-41)

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

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
`shorts-factory` supports two access modes:
- **API key mode** — OpenRouter (default), OpenAI, Anthropic, Gemini, Ollama. **Recommended for reliability.**
- **CLI subscription mode** (experimental):
  - `LLM_PROVIDER=claude-cli` (local dev only — see §5.1)
  - `LLM_PROVIDER=codex-cli` (**user-risk**; verify plan terms permit automation)
  - **Gemini (manual mode)** — documented bash/pwsh workflow only (§5.2)

### USP 2 — HITL gate (script review before burning resources)
`shorts-factory` pauses at `pending_script` state, lets the user read and approve, then continues. Prevents wasted renders on bad scripts.

### USP 3 — Idempotent pipeline (resume from any step)
Each pipeline step logs its result in SQLite. Re-running a job skips already-completed steps. If a step needs to be re-run, use `shorts step reset <job_id> <step>` to invalidate it and all downstream dependencies (see §6.5 for DAG).

### USP 4 — Few-shot voice injection (your approved scripts as examples)
`shorts-factory` accumulates approved scripts as few-shot examples that get injected into future `idea_gen` calls.

---

## 3. Philosophy

**Free by default, configurable everything.**

| Layer | Default | Configurable alternatives |
|---|---|---|
| Idea sources | Google Trends + LLM-generated | Reddit, YouTube API, RSS, custom |
| LLM | OpenRouter (user provides key) | OpenAI, Anthropic, Gemini, Ollama, CLI subs |
| TTS | Edge-TTS (unofficial free, opt-in) | ElevenLabs, OpenAI TTS, local Coqui |
| Clips | Pexels free tier | Pixabay, local folder |
| Publish | YouTube Data API v3 | `--no-publish` to skip |

**Configuration Isolation:** The global configuration (including content from `prompts/system.txt`) is **snapshotted** into the `jobs` table when processing starts. Mid-job changes to `.env` or files do not affect active runs, ensuring deterministic idempotency.

---

## 4. Architecture

### High-level flow
```
[Sources] ──▶ idea_candidates ──▶ [HITL review] ──▶ ideas (draft)
                                                         │
                          ┌──── idea_gen ◀── Few-shot examples (approved scripts)
                          │      OR
                          └──── --script-file (manual injection)
                                                         │
                                               ══ HITL GATE 1 ══
                                               script review + approve
                                                         │
                                tts → bgm_mix → scenes → clips → render
                                                         │
                                         thumbnail → qa_check
                                                         │
                                               ══ HITL GATE 2 ══
                                               pre-upload: ToS/Privacy confirm
                                                         │
                                                   upload_yt
```

### State Machine (SQLite)
**1. Job Level (`jobs` table)**
```
draft → pending_script → processing → pending_upload → completed
                                    ↘ failed
```
**2. Step Level (`step_results` table)**
```
running → done | failed | blocked
```

---

## 5. Provider Layer

### 5.1 CLI adapters — Versioned Contracts
Direct `subprocess.run` calls are routed through an **adapter layer**. The adapter detects the CLI version (e.g., `claude --version` or `codex --version`) and applies the correct parsing contract.

**Subprocess Hardening:**
1. **Stdin input** — No argv leakage.
2. **Environment Allowlist** — Passed via `env` param.
3. **Timeout Enforced**.

```python
# OS-essential + Network proxy variables
SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    "SystemRoot", "TEMP", "TMPDIR", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "COMSPEC", "USERPROFILE"
}
```

### 5.2 Gemini — manual mode
**macOS / Linux:**
```bash
{ cat prompts/system.txt; echo; echo "Idea: Cats..."; } > /tmp/gemini-prompt.txt
gemini < /tmp/gemini-prompt.txt > data/scripts/idea-123.txt
rm /tmp/gemini-prompt.txt
```
**Windows (PowerShell):**
```powershell
$prompt = (Get-Content prompts/system.txt -Raw) + "`n`nIdea: Cats..."
$prompt | Set-Content -Path "$env:TEMP\gemini-prompt.txt" -NoNewline
Get-Content "$env:TEMP\gemini-prompt.txt" -Raw | gemini | Set-Content "data\scripts\idea-123.txt"
Remove-Item "$env:TEMP\gemini-prompt.txt"
```

---

## 6. Idempotent pipeline — state resolution rule

### 6.1 Job Snapshotting
When a job enters `processing`, the orchestrator writes a JSON blob of the current config to `jobs.config_snapshot`. This includes the exact text of system prompts and provider settings.

### 6.2 Step record schema
```sql
CREATE TABLE step_results (
    job_id TEXT,
    step_name TEXT,
    status TEXT,           -- running|done|failed|blocked
    input_hash TEXT,       -- sha256
    provider_id TEXT,
    output_path TEXT,
    output_checksum TEXT,
    lease_owner TEXT,      -- PID@hostname
    lease_heartbeat_at DATETIME,
    attempt_id TEXT,       -- UUID
    PRIMARY KEY (job_id, step_name)
);
```

### 6.3 Directed Acyclic Graph (DAG)
The pipeline follows a fixed order. `shorts step reset` invalidates the target step and all nodes to its right in the sequence:
`idea_gen` → `tts` → `bgm_mix` → `scenes` → `clips` → `render` → `thumbnail` → `qa_check` → `upload_yt`.

### 6.4 YouTube upload — duplicate prevention
1. **System Footer:** Append `\n\n[sf-id: {job_id}]` to the video description. This is pushed "below the fold" via 5+ newlines to preserve UX while enabling deterministic search.
2. **Detection:** On retry, search the user's last 50 uploads for the exact `[sf-id: ...]` string. If found, skip upload and mark `done`.

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security & Remote Access
- **Default Bind:** `127.0.0.1:8765` (Loopback only).
- **Remote Access (LAN/Docker):** To allow other machines, user must set `WEB_BIND=0.0.0.0`.
- **Authentication Flow:** 
  - Token printed to console on boot.
  - Non-loopback access redirects to `/login`.
  - Token is exchanged for a `HttpOnly`, `SameSite=Strict` cookie.
  - CSRF protection required for all POSTs.

---

## 9. Idea Sources
(Remains identical to v1.3)

---

## 10. Docker / Onboarding
**Pattern A (Recommended):** Native Python.
**Pattern B (UNSAFE):** Docker + Credential mount. Documented as high risk.

---

## 13. Changes from v1.4 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 34 | §6.4 | Refine YouTube ID footer ("System Footer") with "below-the-fold" newlines | Reduce user-facing noise while maintaining deterministic searchability |
| 35 | §8.1 | Explicitly define Remote Access model (Loopback vs LAN) | Resolve ambiguity between default security and intended LAN use cases |
| 36 | §5.1 | Clarify CLI adapters apply to both Claude and Codex | Previous wording focused solely on Claude; Codex has identical stability risks |
| 37 | §6.2 | Add `DATETIME` type to SQL schema sketch | Ensure semantic clarity for lease recovery logic |
| 38 | §6.3 | Explicitly define the Pipeline DAG (Directed Acyclic Graph) | Formalize step ordering and "cascade reset" behavior |
| 39 | §9, §10 | Fix editorial numbering gap | Spec jumped from §8 to §10; restored logical flow |
| 40 | §5.2 | Replace Unix syntax in Windows PowerShell examples | Braces and Unix `rm` do not work in native PowerShell; provided native alternatives |
| 41 | §5.1 | Expand `SAFE_ENV_KEYS` (USERPROFILE, COMSPEC) | Enable subprocesses to resolve user paths and shell interpreters on Windows |
