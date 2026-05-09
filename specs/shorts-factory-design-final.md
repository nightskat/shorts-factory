# shorts-factory — Design Spec v1.16

**Date:** 2026-05-09
**Status:** Ready for Implementation — multi-vendor consensus (Claude + Codex + Gemini)
**Author:** Tuan Khuc + Claude
**Changes from v1.15:** see §13 (row 66)

---

## 1. Positioning
(Identical to v1.15)

---

## 2. The 4 USPs

### USP 1 — Bring Your Own LLM (no double billing)
- **API key mode** — OpenRouter (default), OpenAI, Anthropic, Gemini, Ollama.
- **CLI subscription mode** (experimental; user-risk): 
  - `claude-cli`, `codex-cli`.
  - `gemini-cli` (experimental; supported with disclaimer).
- **Gemini (manual mode)** — documented bash/pwsh workflow remains for maximum safety.

---

## 5. Provider Layer

### 5.1 CLI adapters — Versioned Contracts
Direct `subprocess.run` calls are routed through an **adapter layer**.

**`gemini-cli`** — Gemini Pro via `gemini` CLI
- OpenAI-style prompt input supported via `gemini -p "..."`.
- **User responsibility:** Using `gemini-cli` via automated scripts carries potential ToS risks regarding automated access. `shorts-factory` provides this adapter as a convenience but requires the user to accept a risk disclaimer in the Web UI.
- Manual mode (§5.2) is the recommended fallback for strict compliance.

---

## 13. Changes from v1.15 (Gemini refinement)

| # | Section | Change | Reason |
|---|---|---|---|
| 66 | §2, §5.1 | Add `gemini-cli` as an experimental provider | New intelligence suggests `gemini -p` is viable; providing user choice between integrated and manual modes with clear disclaimers |
