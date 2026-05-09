# shorts-factory — Design Spec v1.8

**Date:** 2026-05-09
**Status:** Ready for Implementation — post multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.7:** see §13 (rows 51-52)

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

**Idempotency Tiering:**
- **Pipeline Nodes:** Guaranteed idempotent via local hashes.
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `youtube_upload` record exists.
  - *Tier 2 (Heuristic Fallback):* Best-effort detection via hidden footer search if local DB is lost. Duplicate prevention is NOT guaranteed after DB loss.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
`shorts-factory` accumulates approved scripts as few-shot examples that get injected into future `idea_gen` calls.

---

## 3. Philosophy

**Free by default, configurable everything.**

**Immutable Execution Context:** To ensure total determinism, all inputs (system prompts, frozen few-shot examples, source data, and provider versions) are **snapshotted** into the job record immediately when a job is promoted from `draft`. Subsequent changes to `.env` or files do not affect that specific job (§6.1).

---

## 4. Architecture

### High-level flow
```
[Sources] ──▶ idea_candidates ──▶ [HITL review] ──▶ ideas (draft)
                                                         │
                                          (EXECUTION CONTEXT SNAPSHOT)
                                                         │
                          ┌──── idea_gen ◀── Few-shot examples (FROZEN)
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

---

## 5. Provider Layer

### 5.1 CLI adapters — Versioned Contracts
Direct `subprocess.run` calls are routed through an **adapter layer**. The adapter detects the CLI version (e.g., `claude --version`) and applies the correct parsing contract. Unknown versions attempt to use the latest known contract but trigger a warning log.

**Subprocess Hardening:**
1. **Stdin input** — No argv leakage.
2. **Environment Allowlist** — Prevents credential leakage.
3. **Timeout Enforced**.

---

## 6. Idempotent pipeline — state resolution rule

### 6.1 Execution Context Snapshot
Determinism anchor: a comprehensive JSON blob is written to `jobs.execution_context` the moment a job leaves `draft`. This context includes:
- `system_prompt`: the exact text of the base prompt.
- `few_shot_data`: frozen text of the selected N examples.
- `source_metadata`: the trend/post data used for creation.
- `adapter_contracts`: `{llm: "v0.2", tts: "v1.0"}` versions used.

### 6.2 Step record schema
(Identical to v1.7)

### 6.3 Directed Acyclic Graph (DAG)
`idea_gen` → `tts` → `bgm_mix` → `scenes` → `clips` → `render` → `thumbnail` → `qa_check` → `upload_yt`.

### 6.4 YouTube upload — duplicate prevention
1. **Primary Check:** Orchestrator queries local `youtube_upload` record.
2. **System Footer (Fallback):** Append `\n\n\n\n\n[sf-id: {job_id}]` to the description.
3. **Detection (Best Effort):** If local DB is lost, search last 50 uploads for the footer string. **Note:** User edits or high-volume non-Shorts uploads may defeat this fallback.

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security & Remote Access
- **Default Bind:** `127.0.0.1:8765` (Loopback). Use `WEB_BIND=0.0.0.0` for LAN access.
- **Auth Flow:** console-printed token → `/login` page → `HttpOnly` cookie.
- **CSRF:** Required for all state-changing requests.

---

## 13. Changes from v1.7 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 51 | §3, §4, §6.1 | Expand snapshot to full "Execution Context" (Prompts, Examples, Source Data) | Capturing only config was insufficient; mutable files/examples would still break determinism |
| 52 | §2, §6.4 | Formalize YouTube Idempotency Tiering (Strong vs Heuristic Fallback) | Resolve deceptive "guaranteed idempotency" claim for external side-effects after state loss |
