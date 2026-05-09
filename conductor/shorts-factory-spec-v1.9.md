# shorts-factory — Design Spec v1.9

**Date:** 2026-05-09
**Status:** Ready for Implementation — post multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.8:** see §13 (rows 53-54)

---

## 1. Positioning

### Tagline
> "Turn any idea into a YouTube Short — bring your own LLM, any language, any niche."

### What it is
`shorts-factory` is an open-source, self-hosted **video production pipeline** that automates YouTube Shorts assembly: idea sourcing → script generation → TTS → video render → YouTube upload.

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
`shorts-factory` supports two access modes:
- **API key mode** — OpenRouter (default), OpenAI, Anthropic, Gemini, Ollama.
- **CLI subscription mode** (experimental):
  - `LLM_PROVIDER=claude-cli` (local dev only — see §5.1)
  - `LLM_PROVIDER=codex-cli` (**user-risk**)
  - **Gemini (manual mode)** — documented bash/pwsh workflow only (§5.2)

### USP 2 — HITL gate (script review before burning resources)
`shorts-factory` pauses at `pending_script` state. Prevents wasted renders on bad scripts.

### USP 3 — Idempotent pipeline (resume from any step)
Each pipeline step logs its result in SQLite. Re-running a job skips already-completed steps.

**Idempotency Tiering:**
- **Pipeline Nodes:** Guaranteed idempotent via local hashes.
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `youtube_upload` record exists.
  - *Tier 2 (Heuristic Fallback):* Best-effort detection via hidden footer search if local DB is lost. Duplicate prevention is NOT guaranteed after DB loss.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
`shorts-factory` accumulates approved scripts as few-shot examples.

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
Direct `subprocess.run` calls are routed through an **adapter layer**. The adapter detects the CLI version (e.g., `claude --version`) and applies the correct parsing contract.

**Subprocess Hardening:**
1. **Stdin input** — No argv leakage.
2. **Environment Allowlist** — Prevents credential leakage.
3. **Timeout Enforced**.

---

## 6. Idempotent pipeline — state resolution rule

### 6.1 Execution Context Snapshot
Determinism anchor: a comprehensive JSON blob is written to `jobs.execution_context` the moment a job leaves `draft`. This context includes:
- `system_prompt`: exact base prompt text.
- `few_shot_data`: frozen text of selected N examples.
- `source_metadata`: trend/post data used for creation.
- `adapter_contracts`: `{llm: "v0.2", tts: "v1.0"}`.

### 6.2 Step record schema
(Identical to v1.7)

### 6.3 Concurrency — Worker Lease Model
To prevent race conditions and duplicate renders, workers must claim a step via an atomic `lease`:
1. **Acquisition:** `UPDATE step_results SET status='running', lease_owner='PID@host', lease_heartbeat_at=NOW() WHERE job_id=? AND step_name=? AND (status IN ('failed', 'blocked') OR lease_heartbeat_at < NOW() - 2min)`.
2. **Heartbeat:** Active workers update `lease_heartbeat_at` every 30s.
3. **Release:** Upon completion, `status` set to `done`, `lease_owner` cleared.
4. **Collision:** If acquisition fails, worker logs "Step locked by other process" and exits or waits.

### 6.4 YouTube upload — Two-Phase Side-Effect Protocol
1. **Phase 1: Pre-Commit (Local).** Persist `youtube_upload` record with `status='started'`, `job_id`, and a deterministic `idempotency_key`. 
2. **Phase 2: External Call.** Execute upload. Append `\n\n\n\n\n[sf-id: {job_id}]` to description.
3. **Phase 3: Post-Commit (Local).** Update record to `status='completed'`.
4. **Crash Recovery:** On restart, if a record is in `status='started'`, the worker MUST search the user's last 50 uploads for the `[sf-id: ...]` footer *before* attempting a new upload.

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security & Remote Access
- **Default Bind:** `127.0.0.1:8765` (Loopback).
- **Auth Flow:** console-printed token → `/login` page → `HttpOnly` cookie.
- **CSRF:** Required for all state-changing requests.

---

## 13. Changes from v1.8 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 53 | §6.3 | Restore and formalize atomic Worker Lease Model | Prevent concurrent execution/artifacts corruption by multiple runners or UI clicks |
| 54 | §6.4 | Implement Two-Phase Side-Effect Protocol for YouTube uploads | Ensure crash-safety during external API calls; prevent duplicates if process dies mid-upload |
