# shorts-factory — Design Spec v1.10

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.9:** see §13 (rows 55-57)

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
- **Local Nodes:** Guaranteed idempotent via hashes/local state.
- **YouTube Upload:** 
  - *Tier 1 (Strong):* Idempotent while local `completed` record exists.
  - *Tier 2 (Reconciliation Gate):* After local state loss or crash, system enters a `blocked` state for manual verification (see §6.4). Duplicate prevention is NOT auto-guaranteed after crash/loss.

### USP 4 — Few-shot voice injection (your approved scripts as examples)
`shorts-factory` accumulates approved scripts as few-shot examples.

---

## 3. Philosophy

**Free by default, configurable everything.**

**Total Execution Snapshots:** To ensure absolute determinism, all outcome-affecting inputs are **snapshotted** into the job record immediately upon promotion from `draft`. Subsequent changes to `.env` or system files do not affect that job (§6.1).

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

### 6.1 Total Execution Context Snapshot
Determinism anchor: a comprehensive JSON blob is written to `jobs.execution_context` the moment a job leaves `draft`. This context includes:
- **Prompts:** Exact text of system and user templates.
- **Few-shot Data:** Frozen text content of the selected N examples.
- **Generation Hyperparams:** Provider name, Model ID, temperature, top-p, max-tokens.
- **TTS Settings:** Voice ID, Model name, speed, pitch.
- **Render Settings:** Resolution, framerate, background music volume levels.
- **Target Language:** Locale code used for generation and TTS.
- **Adapter Contracts:** Specific version IDs (e.g., `{llm: "v0.2"}`) for CLI providers.

### 6.2 Step record schema
(Identical to v1.7)

### 6.3 Concurrency — Worker Lease Model
To prevent race conditions, workers must claim a step via an atomic lease:
1. **Acquisition:** 
   ```sql
   UPDATE step_results 
   SET status='running', lease_owner='PID@host', lease_heartbeat_at=NOW() 
   WHERE job_id=? AND step_name=? 
   AND status NOT IN ('done', 'skipped')
   AND (status IN ('failed', 'blocked') OR (status='running' AND lease_heartbeat_at < NOW() - 2min))
   ```
2. **Heartbeat:** Active workers update `lease_heartbeat_at` every 30s.
3. **Release:** Upon completion, `status` set to `done`, `lease_owner` cleared.

### 6.4 YouTube upload — Manual Reconciliation Gate
1. **Phase 1: Pre-Commit.** Persist `youtube_upload` record with `status='started'`.
2. **Phase 2: External Call.** Execute upload with hidden footer `[sf-id: {job_id}]`.
3. **Phase 3: Post-Commit.** Update record to `status='completed'`.
4. **Crash Recovery (The Gate):** On restart, if a record is in `status='started'`, the worker:
   - Searches the user's last 50 uploads for the footer.
   - If found, marks `completed`.
   - If **NOT** found, the step moves to `blocked` status.
   - **HITL Resolution:** User sees a prompt in the `/pipeline` tab: "System crashed during upload. We couldn't find a duplicate on YouTube. [Upload Again] or [Mark as Done manually with Video ID: ___]".

---

## 8. Web UI (FastAPI, 4 tabs)

### 8.1 Security & Remote Access
- **Default Bind:** `127.0.0.1:8765` (Loopback). Use `WEB_BIND=0.0.0.0` for LAN access.
- **Auth Flow:** console-printed token → `/login` page → `HttpOnly` cookie.
- **CSRF:** Required for all state-changing requests.

---

## 13. Changes from v1.9 (adversarial review fixes)

| # | Section | Change | Reason |
|---|---|---|---|
| 55 | §6.3 | Refine Lease Acquisition predicate | Ensure 'done' steps are never overtaken by stale heartbeat logic |
| 56 | §3, §6.1 | Expand snapshot to "Total Execution Context" | Include all hyperparameters and settings to ensure real-world determinism |
| 57 | §2, §6.4 | Implement Manual Reconciliation Gate for YouTube | Replace deceptive automation with safe HITL recovery for crashed uploads |
