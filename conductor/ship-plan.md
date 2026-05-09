# Shorts Factory — Full Build & Ship Plan

**Goal:** Build, test, and ship the entire `shorts-factory` repository today, adhering strictly to the `shorts-factory-design-final.md` (v1.15) spec.

**Strategy:** Divide the remaining architecture into 4 distinct phases. Each phase will follow a rigorous `Implement → Test → Adversarial Review (CVAR) → Debate (if needed)` cycle.

---

## Phase 1: Core Providers & Voice System
Implement the foundational data generation and external API communication layers.

*   **Task 1.1: LLM Adapters.** Implement `LLMProvider` interface, `OpenRouter` adapter, and the hardened CLI adapters (`claude_cli`, `codex_cli`) with stdin/timeout/env-allowlist.
*   **Task 1.2: Media Providers.** Implement `Edge-TTS` and `Pexels` stock footage provider.
*   **Task 1.3: Voice Profile System.** Implement `shorts/voice/examples.py` for seed management and `injector.py` for few-shot prompt assembly.
*   **Phase 1 Gate:** Unit tests passing + CVAR (Focus: ToS compliance in CLI adapters, Prompt leakage).

## Phase 2: Idempotent Orchestrator & Nodes
Build the pipeline nodes and the state machine that ties them together.

*   **Task 2.1: Pipeline Engine.** Implement `shorts/pipeline.py`. Must strictly follow the DAG, Snapshotting, and Worker Lease (Winner-Take-All) mechanics.
*   **Task 2.2: Generator Nodes.** Implement `idea_gen.py`, `tts.py`, `bgm_mix.py`.
*   **Task 2.3: Video Assembly Nodes.** Implement `scenes.py`, `clips.py`, `render.py` (ffmpeg abstraction), and `thumbnail.py`.
*   **Task 2.4: YouTube Upload Node.** Implement `qa_check.py` and `upload_yt.py` with the Two-Phase Side-Effect Protocol (Hidden footer).
*   **Phase 2 Gate:** E2E Pipeline mock test + CVAR (Focus: Concurrency races, idempotency leaks). *Any blockers here trigger a 3-way debate.*

## Phase 3: User Interfaces (Web & CLI)
Expose the pipeline to the user with secure defaults.

*   **Task 3.1: Security & Auth.** Implement static token generation and `HttpOnly` cookie + CSRF middleware for FastAPI.
*   **Task 3.2: Web API & Views.** Build the 4 tabs (`/ideas`, `/pipeline`, `/voice`, `/config`) using basic Jinja2 templates or minimal React/HTML. Implement Manual Script Injection and the Pre-Upload HITL Gate.
*   **Task 3.3: CLI Entrypoint.** Implement `shorts/cli.py` (commands: `serve`, `run`, `step reset`, `voice seed`).
*   **Phase 3 Gate:** API security test + CVAR (Focus: Auth bypass, CSRF vulnerabilities).

## Phase 4: Packaging & Shipping
Prepare the repo for public release.

*   **Task 4.1: Environment & Docker.** Finalize `.env.example`, `docker-compose.yml` (Pattern A), and `docker-compose.cli.yml` (Pattern B - Unsafe).
*   **Task 4.2: Documentation.** Write `README.md` (installation, USPs) and `docs/gemini-manual-mode.md`.
*   **Phase 4 Gate:** Final repo integrity check + CVAR.

---

### Operating Rules
1.  **Parallel Dispatch:** Where tasks are independent (e.g., TTS provider vs LLM provider), dispatch parallel subagents to maximize speed.
2.  **Dispute Resolution:** If CVAR identifies an architectural conflict or a P0 security issue that isn't easily solved, use the `debate` skill (Claude vs Codex vs Gemini) to vote on the solution.
3.  **Checkpoints:** Log progress to `data/rollouts/build-cycle.jsonl` after every phase.
