# Phase 1: Core Providers & Voice System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute this plan in strict TDD order. Every implementation step starts with a failing test and ends with the narrowest possible passing run.

**Goal:** Implement the Phase 1 provider layer and voice system for `shorts-factory`: LLM adapters, media providers, and deterministic few-shot voice injection.

**Architecture:** Keep provider code thin and testable. Put contracts in base classes, provider selection in factories, CLI risk controls in a shared subprocess helper, and voice persistence/injection in isolated modules that can later plug into `idea_gen`.

**Tech Stack:** Python 3.11+, pytest, sqlite3, `requests` or `httpx` for OpenRouter/Pexels, `edge-tts`, subprocess for CLI providers.

---

## Non-Negotiables

- [ ] All provider components ship with unit tests before implementation.
- [ ] CLI adapters must use **stdin-only prompt input**. Prompt text must never appear in argv.
- [ ] CLI adapters must pass a **strict env allowlist** to child processes.
- [ ] CLI adapters must enforce a **timeout** on every subprocess call.
- [ ] Versioned CLI contracts must be probed once and cached per process.
- [ ] Voice injection output must be deterministic for the same inputs and example ordering.
- [ ] No live network or live CLI binaries in unit tests. Mock all external boundaries.

---

## Task 1: Test Harness and Provider Skeleton

**Files:**
- Create: `tests/providers/__init__.py`
- Create: `tests/providers/llm/test_factory.py`
- Create: `tests/providers/llm/test_base.py`
- Create: `tests/providers/tts/test_base.py`
- Create: `tests/providers/clips/test_base.py`
- Create: `tests/voice/test_injector.py`
- Create: `tests/voice/test_examples.py`

- [ ] **Step 1:** Create provider and voice test directories plus `__init__.py` files.
- [ ] **Step 2:** Write a failing LLM base contract test for `LLMProvider`.
- [ ] **Step 3:** Write failing base contract tests for `TTSProvider` and `ClipsProvider`.
- [ ] **Step 4:** Write a failing factory smoke test expecting unknown provider names to raise a clear error.
- [ ] **Step 5:** Run `rtk pytest tests/providers tests/voice -q` and confirm failures are on missing modules only.

---

## Task 2: LLM Base Contract and Factory

**Files:**
- Create: `shorts/providers/llm/base.py`
- Create: `shorts/providers/llm/factory.py`

- [ ] **Step 1:** Implement the minimal `LLMProvider` abstract interface with `complete(...)` and `name()`.
- [ ] **Step 2:** Add a tiny metadata surface for `provider_id` and `contract_version`.
- [ ] **Step 3:** Write a failing factory test for `openrouter`.
- [ ] **Step 4:** Implement factory resolution for `openrouter`.
- [ ] **Step 5:** Write failing factory tests for `claude-cli` and `codex-cli`.
- [ ] **Step 6:** Implement factory resolution for `claude-cli` and `codex-cli`.
- [ ] **Step 7:** Run `rtk pytest tests/providers/llm/test_base.py tests/providers/llm/test_factory.py -q`.

---

## Task 3: Shared CLI Subprocess Hardening Helper

**Files:**
- Create: `shorts/providers/llm/cli_subprocess.py`
- Create: `tests/providers/llm/test_cli_subprocess.py`

**Hardening Rules to Implement and Test:**
- Prompt payload enters the child process through `stdin` only.
- Child argv contains flags and executable only, never prompt text.
- Child env is built from an allowlist only.
- Child process timeout defaults to `LLM_TIMEOUT_SEC` or `120`.
- Timeout failure raises a structured provider error with no prompt echo.
- Non-zero exit raises a structured provider error with stderr captured safely.
- Missing executable raises a clear install/auth guidance error.

**Env allowlist for child processes:**
- `PATH`, `HOME`, `USERPROFILE`, `LANG`, `LC_ALL`, `TERM`, `TMPDIR`, `TEMP`, `TMP`, `SYSTEMROOT`, `COMSPEC`, `PATHEXT`, `APPDATA`, `LOCALAPPDATA`, `NO_COLOR`, `CI`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`

- [ ] **Step 1:** Write a failing test asserting prompt text is sent via `stdin` and absent from argv.
- [ ] **Step 2:** Write a failing test asserting non-allowlisted env vars are stripped.
- [ ] **Step 3:** Write a failing test asserting timeout is passed to `subprocess.run`.
- [ ] **Step 4:** Implement the helper and the allowlisted env builder.
- [ ] **Step 5:** Write a failing test for non-zero exit handling.
- [ ] **Step 6:** Write a failing test for missing binary handling.
- [ ] **Step 7:** Implement structured error mapping.
- [ ] **Step 8:** Run `rtk pytest tests/providers/llm/test_cli_subprocess.py -q`.

---

## Task 4: OpenRouter Adapter

**Files:**
- Create: `shorts/providers/llm/openrouter.py`
- Create: `tests/providers/llm/test_openrouter.py`

- [ ] **Step 1:** Write a failing test for request payload shape: system prompt, user prompt, model, temperature.
- [ ] **Step 2:** Write a failing test for `X-Idempotency-Key` header generation.
- [ ] **Step 3:** Write a failing test for auth header usage from env/config.
- [ ] **Step 4:** Implement the minimal adapter with a mocked HTTP client boundary.
- [ ] **Step 5:** Write a failing test for successful response parsing into plain text.
- [ ] **Step 6:** Write a failing test for malformed/empty provider responses.
- [ ] **Step 7:** Implement response parsing and error handling.
- [ ] **Step 8:** Run `rtk pytest tests/providers/llm/test_openrouter.py -q`.

---

## Task 5: Claude CLI Adapter

**Files:**
- Create: `shorts/providers/llm/claude_cli.py`
- Create: `tests/providers/llm/test_claude_cli.py`

- [ ] **Step 1:** Write a failing test for version probing via `claude --version`.
- [ ] **Step 2:** Write a failing test for caching the detected contract version.
- [ ] **Step 3:** Write a failing test asserting provider execution goes through `cli_subprocess.py`.
- [ ] **Step 4:** Implement version probe and contract cache.
- [ ] **Step 5:** Write a failing test for JSON contract parsing.
- [ ] **Step 6:** Write a failing test for safe error messaging when the CLI returns bad output.
- [ ] **Step 7:** Implement `complete(...)` using stdin-fed prompt assembly and parsed output.
- [ ] **Step 8:** Add a test asserting provider metadata marks this adapter as `local-only` or equivalent warning state.
- [ ] **Step 9:** Run `rtk pytest tests/providers/llm/test_claude_cli.py -q`.

---

## Task 6: Codex CLI Adapter

**Files:**
- Create: `shorts/providers/llm/codex_cli.py`
- Create: `tests/providers/llm/test_codex_cli.py`

- [ ] **Step 1:** Write a failing test for version probing via `codex --version` or the selected non-interactive version command.
- [ ] **Step 2:** Write a failing test for contract caching.
- [ ] **Step 3:** Write a failing test asserting prompt input is passed only through stdin.
- [ ] **Step 4:** Implement version probe and cached contract selection.
- [ ] **Step 5:** Write a failing test for expected JSON output parsing.
- [ ] **Step 6:** Write a failing test for malformed CLI JSON output.
- [ ] **Step 7:** Implement `complete(...)` through the shared hardened subprocess helper.
- [ ] **Step 8:** Add a test asserting provider metadata marks this adapter as experimental or user-risk.
- [ ] **Step 9:** Run `rtk pytest tests/providers/llm/test_codex_cli.py -q`.

---

## Task 7: TTS Base and Edge-TTS Provider

**Files:**
- Create: `shorts/providers/tts/base.py`
- Create: `shorts/providers/tts/edge_tts.py`
- Create: `tests/providers/tts/test_edge_tts.py`

- [ ] **Step 1:** Implement the minimal `TTSProvider` abstract interface after the base test is failing.
- [ ] **Step 2:** Write a failing test for `EdgeTTSProvider` constructor/config validation.
- [ ] **Step 3:** Write a failing test for text, voice, rate, and pitch mapping to the library call.
- [ ] **Step 4:** Implement the adapter against a mocked `edge_tts` boundary.
- [ ] **Step 5:** Write a failing test for output file creation contract or returned path.
- [ ] **Step 6:** Write a failing test for provider exception wrapping.
- [ ] **Step 7:** Implement output handling and error mapping.
- [ ] **Step 8:** Run `rtk pytest tests/providers/tts/test_base.py tests/providers/tts/test_edge_tts.py -q`.

---

## Task 8: Clips Base and Pexels Provider

**Files:**
- Create: `shorts/providers/clips/base.py`
- Create: `shorts/providers/clips/pexels.py`
- Create: `tests/providers/clips/test_pexels.py`

- [ ] **Step 1:** Implement the minimal `ClipsProvider` abstract interface after the base test is failing.
- [ ] **Step 2:** Write a failing test for Pexels auth header usage.
- [ ] **Step 3:** Write a failing test for normalized clip search results.
- [ ] **Step 4:** Implement the minimal search adapter with a mocked HTTP boundary.
- [ ] **Step 5:** Write a failing test for portrait-oriented filtering or ranking behavior.
- [ ] **Step 6:** Write a failing test for empty-result handling.
- [ ] **Step 7:** Implement filtering, normalization, and safe empty responses.
- [ ] **Step 8:** Run `rtk pytest tests/providers/clips/test_base.py tests/providers/clips/test_pexels.py -q`.

---

## Task 9: Voice Example Store

**Files:**
- Create: `shorts/voice/examples.py`
- Create: `tests/voice/test_examples.py`

**Suggested scope for v1:**
- Insert seed scripts into `voice_examples`
- Insert approved scripts into `approved_scripts`
- List unified examples for inspection
- Select top `N` examples deterministically by recency, with simple optional edit-delta weighting where data exists

- [ ] **Step 1:** Write a failing test for adding a seed example into `voice_examples`.
- [ ] **Step 2:** Write a failing test for adding an approved script into `approved_scripts`.
- [ ] **Step 3:** Implement minimal insert helpers against a temp SQLite DB.
- [ ] **Step 4:** Write a failing test for listing merged examples in deterministic order.
- [ ] **Step 5:** Implement list/query helpers.
- [ ] **Step 6:** Write a failing test for `get_top_examples(limit=3)` selection.
- [ ] **Step 7:** Implement deterministic selection rules and tie-breaking.
- [ ] **Step 8:** Run `rtk pytest tests/voice/test_examples.py -q`.

---

## Task 10: Few-Shot Injector

**Files:**
- Create: `shorts/voice/injector.py`
- Create: `tests/voice/test_injector.py`

- [ ] **Step 1:** Write a failing test for zero-example behavior returning the base prompt unchanged.
- [ ] **Step 2:** Write a failing test for one-example formatting.
- [ ] **Step 3:** Write a failing test for multiple-example ordering stability.
- [ ] **Step 4:** Implement the minimal formatter and injector helpers.
- [ ] **Step 5:** Write a failing test asserting exact deterministic output for the same base prompt and example list.
- [ ] **Step 6:** Write a failing test asserting examples are clearly delimited to reduce prompt leakage/misparsing.
- [ ] **Step 7:** Implement final formatting rules.
- [ ] **Step 8:** Run `rtk pytest tests/voice/test_injector.py -q`.

---

## Task 11: Cross-Component Integration Tests

**Files:**
- Create: `tests/providers/llm/test_factory_integration.py`
- Create: `tests/voice/test_voice_llm_integration.py`

- [ ] **Step 1:** Write a failing test asserting the LLM factory returns the correct adapter for each configured provider string.
- [ ] **Step 2:** Write a failing test asserting injected few-shot prompt text is accepted by an LLM provider mock without altering example order.
- [ ] **Step 3:** Implement any thin glue needed between factory and adapters.
- [ ] **Step 4:** Run `rtk pytest tests/providers/llm/test_factory_integration.py tests/voice/test_voice_llm_integration.py -q`.

---

## Task 12: Phase 1 Gate

**Files:**
- Modify if needed: `docs/cli-providers-tos.md`
- Optional: `data/rollouts/build-cycle.jsonl` via existing rollout utility during implementation, not in this plan artifact

- [ ] **Step 1:** Run the full Phase 1 unit suite: `rtk pytest tests/providers tests/voice -q`.
- [ ] **Step 2:** Run the full repo test suite to catch regressions: `rtk pytest -q`.
- [ ] **Step 3:** Perform a manual adversarial pass on CLI adapters for prompt leakage, env leakage, and timeout bypass paths.
- [ ] **Step 4:** Verify both CLI adapters expose clear user-facing install/login guidance without embedding secrets or prompt text.
- [ ] **Step 5:** Verify OpenRouter and Pexels tests never hit the live network.
- [ ] **Step 6:** Mark Phase 1 complete only when all tests pass and the CLI hardening checklist is satisfied.
