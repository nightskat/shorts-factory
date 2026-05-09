# shorts-factory — Design Spec v1.7

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.6:** see §13 (rows 49-50)

---

## 1. Positioning

### Tagline
> "Turn any idea into a YouTube Short — bring your own LLM, any language, any niche."

### What it is
`shorts-factory` is an open-source, self-hosted **video production pipeline** that automates YouTube Shorts assembly: idea sourcing → script generation → TTS → video render → YouTube upload.

### What it is NOT (v1)
- Not a SaaS product (that comes later)
- Not a clip-from-existing-video tool
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
Each pipeline step logs its result in SQLite. Re-running a job skips already-completed steps. If a step needs to be re-run, use `shorts step reset <job_id> <step>` to invalidate it and all downstream dependencies (see §6.3 for DAG).

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

**Configuration Isolation:** To ensure total determinism, configuration is **snapshotted** into the job record immediately when a job is promoted from `draft`. Mid-job changes to `.env` or files do not affect the generated script or the rendering pipeline for that job (§6.1).

---

## 4. Architecture

### High-level flow
```
[Sources] ──▶ idea_candidates ──▶ [HITL review] ──▶ ideas (draft)
                                                         │
                                               (SNAPSHOT CONFIG)
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
**1. Job Level (`jobs` table)** - tracks overall progression. All non-terminal states can transition to `failed`.
```
draft → pending_script → processing → pending_upload → completed
      ↘                ↘            ↘                ↘
        ─────────────▶ ( failed ) ◀───────────────────
```
**2. Step Level (`step_results` table)** - tracks individual node execution.
```
running → done | failed | blocked
```

---

## 5. Provider Layer

### 5.1 CLI adapters — Versioned Contracts
Direct `subprocess.run` calls are routed through an **adapter layer**. The adapter detects the CLI version (e.g., `claude --version` or `codex --version`) and applies the correct parsing contract. Unknown versions attempt to use the latest known contract but trigger a warning log.

**Subprocess Hardening:**
1. **Stdin input** — No argv leakage.
2. **Environment Allowlist** — Prevents credential leakage.
3. **Timeout Enforced**.

```python
# Expanded for cross-platform config discovery and proxies
SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    "SystemRoot", "TEMP", "TMPDIR", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "COMSPEC", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME"
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

**Privacy Note:** Writing prompts to temp files exposes data to other local users. Use stdin pipes where possible. On crash, temporary files may persist; the `shorts doctor` utility should clean these.

---

## 6. Idempotent pipeline — state resolution rule

### 6.1 Job Snapshotting
Determinism anchor: config is snapshotted to `jobs.config_snapshot` JSON column the moment a job leaves `draft`. This ensures the script is generated and the video is rendered using identical prompts/settings, even if the job sits in `pending_script` for days while the global `.env` evolves.

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
`shorts step reset` invalidates the target step and all nodes to its right:
`idea_gen` → `tts` → `bgm_mix` → `scenes` → `clips` → `render` → `thumbnail` → `qa_check` → `upload_yt`.

### 6.4 YouTube upload — duplicate prevention
1. **Primary Check:** Orchestrator queries the local `youtube_upload` record for existing success.
2. **System Footer (Fallback):** Append `\n\n\n\n\n[sf-id: {job_id}]` to the description. This pushes the ID "below the fold."
3. **Detection (Best Effort):** On retry, if no local success record exists, search the user's last 50 uploads for the exact `[sf-id: ...]` string. This is a heuristic fallback only (user edits or high-volume uploads may defeat it).

---

## 7. Few-shot Voice System

### Tables (SQLite)
- `voice_examples`: manually added seed scripts.
- `approved_scripts`: user-approved scripts + edit delta + timestamp.

### Injection
`examples = voice_store.get_top_examples(n=3, weight_by="recency")`. No fine-tuning required.

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security & Remote Access
- **Default Bind:** `127.0.0.1:8765` (Loopback). Use `WEB_BIND=0.0.0.0` for LAN access.
- **Auth Flow:** консоль-printed token → `/login` page → `HttpOnly` cookie.
- **CSRF:** Required for all state-changing requests.

---

## 9. Idea Sources
(Remains identical to v1.3)

---

## 10. Docker / Onboarding
**Pattern A (Recommended):** Native Python.
**Pattern B (UNSAFE):** Docker + Credential mount. Account-takeover risk.

---

## 13. Changes from v1.6 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 49 | §3, §4, §6.1 | Anchor config snapshotting to Job Creation / Promotion from `draft` | Fix idempotency contradiction; ensure script generation and rendering use same config |
| 50 | §4 | Refine Job state machine to include failure paths from all states | Close control-plane gap for pre-processing and HITL-stage errors |
