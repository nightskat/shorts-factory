# shorts-factory — Design Spec v1.15

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.14:** see §13 (rows 64-65)

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
- **Remote Provider Nodes (LLM, TTS):** Tiered protection (§6.5).
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `completed` record exists.
  - *Tier 2 (Manual Reconciliation):* After crash/loss, system enters `blocked` for HITL verification.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
Accumulates approved scripts as few-shot examples for future generation.

---

## 3. Philosophy

**Prompt & Parameter Determinism:** All execution-critical inputs are **snapshotted** into the job record when a job leaves `draft` (§6.1). 

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
Determinism anchor: a JSON blob in `jobs.execution_context` frozen at job promotion.

### 6.2 Step record schema
(Identical to v1.7)

### 6.3 Concurrency — Worker Lease Model (SQLite)
To prevent race conditions and handle crashes, workers must claim a step via an atomic lease:
1. **Initiation (New Steps):** `INSERT OR IGNORE INTO step_results (job_id, step_name, status, lease_owner, lease_heartbeat_at) VALUES (?, ?, 'running', 'PID@host', STRFTIME('%s', 'now'))`.
2. **Acquisition (Resumes/Recovery):** If `INSERT` affects 0 rows:
   ```sql
   UPDATE step_results 
   SET status='running', lease_owner='PID@host', lease_heartbeat_at=STRFTIME('%s', 'now') 
   WHERE job_id=? AND step_name=? 
   AND status NOT IN ('done', 'skipped', 'blocked') -- 'blocked' requires human reset
   AND (status = 'failed' OR (status = 'running' AND CAST(lease_heartbeat_at AS INTEGER) < STRFTIME('%s', 'now') - 120))
   ```
3. **Winner-Take-All Rule:** A worker **MUST ONLY** proceed to execution if the `INSERT` or `UPDATE` affected exactly 1 row.
4. **Out-of-Band Heartbeat:** Workers MUST update `lease_heartbeat_at` every 30s using a **background thread**. This ensures the lease remains valid during blocking operations (rendering, uploads).

### 6.4 YouTube upload — Manual Reconciliation Gate
(Identical to v1.10)

### 6.5 Remote Side-Effect Protection Matrix (LLM, TTS)
(Identical to v1.14)

---

## 8. Web UI (FastAPI)
(Identical to v1.10)

---

## 13. Changes from v1.14 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 64 | §6.3 | Exclude `blocked` status from automatic lease takeover | Prevent automated workers from bypassing human-required HITL gates or reconciliation pauses |
| 65 | §6.3 | Mandate "Out-of-Band" (background thread) heartbeats | Ensure leases do not expire during long synchronous operations like rendering or network-heavy uploads |
