# shorts-factory — Design Spec v1.13

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.12:** see §13 (row 61)

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
- **Remote Provider Nodes (LLM, TTS):** Protected via artifact-existence checks and provider-level idempotency keys (§6.5).
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `completed` record exists.
  - *Tier 2 (Manual Reconciliation):* After crash/loss, system enters `blocked` for HITL verification.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
Accumulates approved scripts as few-shot examples for future generation.

---

## 3. Philosophy

**Prompt & Parameter Determinism:** All execution-critical inputs (prompts, few-shot examples, hyperparameters, and voices) are **snapshotted** into the job record when a job leaves `draft`. This ensures the core logic remains stable even if system-wide prompts or `.env` settings are updated mid-run (§6.1). 

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
1. **Initiation:** `INSERT OR IGNORE`.
2. **Acquisition:** `UPDATE ... WHERE ... AND status NOT IN ('done', 'skipped') AND (...)`.
3. **Winner-Take-All Rule:** Worker **MUST ONLY** proceed if affected rows == 1.
4. **Heartbeat:** Every 30s.

### 6.4 YouTube upload — Manual Reconciliation Gate
1. **Phase 1: Pre-Commit.** 
2. **Phase 2: External Call.** 
3. **Phase 3: Post-Commit.** 
4. **Crash Recovery:** Search fallback → move to `blocked` for manual verification if missing.

### 6.5 Remote Side-Effect Protection (LLM, TTS)
To prevent double-billing and artifact divergence on crash-retry:
1. **Artifact-First Recovery:** Before calling a provider, the worker checks if the expected output file (path derived from `job_id` + `input_hash`) already exists on disk. If found and valid, the worker updates DB to `done` and skips the call.
2. **Idempotency Keys:** For providers supporting it (OpenRouter, OpenAI), the framework MUST send a header `X-Idempotency-Key: SHA256(job_id + step_name + input_hash)`.

---

## 8. Web UI (FastAPI)
(Identical to v1.10)

---

## 13. Changes from v1.12 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 61 | §6.5 | Implement Universal Remote Idempotency (Artifact-first + Keys) | Prevent double-billing and logic divergence for LLM and TTS calls after process crash |
