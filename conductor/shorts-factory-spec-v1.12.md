# shorts-factory — Design Spec v1.12

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.11:** see §13 (row 60)

---

## 1. Positioning

### Tagline
> "Turn any idea into a YouTube Short — bring your own LLM, any language, any niche."

### What it is
`shorts-factory` is an open-source, self-hosted **video production pipeline** that automates YouTube Shorts assembly: idea sourcing → script generation → TTS → video render → YouTube upload.

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
- **API key mode** — OpenRouter (default), OpenAI, Anthropic, Gemini, Ollama.
- **CLI subscription mode** (experimental): `claude-cli`, `codex-cli`.
- **Gemini (manual mode)** — documented bash/pwsh workflow.

### USP 2 — HITL gate (script review before burning resources)
Pauses at `pending_script` state for user approval.

### USP 3 — Idempotent pipeline (resume from any step)
Each pipeline step logs result in SQLite. Re-running a job skips already-completed steps.

**Idempotency Tiering:**
- **Local Nodes:** Config-idempotent via frozen hashes.
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `completed` record exists.
  - *Tier 2 (Manual Reconciliation):* After crash/loss, system enters `blocked` for HITL verification.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
Accumulates approved scripts as few-shot examples for future generation.

---

## 3. Philosophy

**Prompt & Parameter Determinism:** All execution-critical inputs (prompts, few-shot examples, hyperparameters, and voices) are **snapshotted** into the job record when a job leaves `draft`. This ensures the core logic remains stable even if system-wide prompts or `.env` settings are updated mid-run (§6.1). 
*Note: Low-level toolchain binaries (e.g., ffmpeg) and local media assets are assumed stable and are not hashed in v1.0.*

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
(Identical to v1.10)

---

## 6. Idempotent pipeline — state resolution rule

### 6.1 Execution Context Snapshot
Determinism anchor: a JSON blob in `jobs.execution_context` frozen at job promotion. Includes:
- **Prompts:** Exact text of templates.
- **Few-shot Data:** Frozen text of selected examples.
- **Params:** Model IDs, temperatures, voices, resolutions, language.

### 6.2 Step record schema
(Identical to v1.7)

### 6.3 Concurrency — Worker Lease Model (SQLite)
To claim a step, a worker follows this atomic sequence:
1. **Initiation (New Steps):** `INSERT OR IGNORE INTO step_results (job_id, step_name, status, lease_owner, lease_heartbeat_at) VALUES (?, ?, 'running', 'PID@host', STRFTIME('%s', 'now'))`.
2. **Acquisition (Resumes/Crashes):** If `INSERT` affected 0 rows, worker attempts:
   ```sql
   UPDATE step_results 
   SET status='running', lease_owner='PID@host', lease_heartbeat_at=STRFTIME('%s', 'now') 
   WHERE job_id=? AND step_name=? 
   AND status NOT IN ('done', 'skipped')
   AND (status IN ('failed', 'blocked') OR (status='running' AND CAST(lease_heartbeat_at AS INTEGER) < STRFTIME('%s', 'now') - 120))
   ```
3. **Winner-Take-All Rule:** A worker **MUST ONLY** proceed to execution if the `INSERT` (step 1) or `UPDATE` (step 2) call affected exactly 1 row. If 0 rows are affected, the worker must abort or wait (lease is held by another active process).
4. **Heartbeat:** Update `lease_heartbeat_at` every 30s.

### 6.4 YouTube upload — Manual Reconciliation Gate
(Identical to v1.10)

---

## 8. Web UI (FastAPI)
(Identical to v1.10)

---

## 13. Changes from v1.11 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 60 | §6.3 | Formalize "Winner-Take-All" clause (1 row affected) | Prevent losers of the lease race from continuing execution and causing duplicate side effects |
