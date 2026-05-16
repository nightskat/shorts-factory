# AGENTS.md — Rules for AI Agents working on shorts-factory

This file is read by Jules, Codex, Claude Code, and Gemini CLI. Follow these rules on every PR.

## 🛑 Branch hygiene (MUST)

### 1. Rebase, never merge
- Use `git rebase origin/main` to update a feature branch.
- **NEVER** run `git merge main` into a feature branch — it floods the PR with unrelated diffs from intermediate commits on main.
- If a rebase conflict is too noisy to resolve, ask the maintainer instead of merging main as a shortcut.

### 2. Verify diff before push
```bash
git fetch origin main
git diff --stat origin/main..HEAD     # MUST match PR title scope
```
- A "Refactor `foo.py`" PR must touch ≤2 files (the file + its test).
- A "Add tests for X module" PR must touch only the new test file.
- A "Fix Y" PR must touch only files implementing the fix.
- If `git diff --stat` shows >5 files for a single-concern PR, **stop and reset the branch** — do not push.

### 3. One concern per PR
- If you finish refactor A and find unrelated improvements for B, open a **separate** PR for B.
- Do not bundle "improvements I noticed while doing X" into the X PR.

### 4. Never commit scratch files
The following are gitignored and must never be tracked:
- `commit_message.txt` — write commit messages directly via `git commit -m` or `--file=-`.
- `rewrite_tests.py` — use proper scripts in `scripts/` if needed, or run ad-hoc and don't save.
- `.Jules/` — typo of `.jules/`. Capital `J` is a bug; correct path is lowercase `.jules/`.

### 5. Test-file churn
If your PR is not about tests, do not modify test files at all — not even to remove blank lines or sort imports. That diff signals scope creep.

## 🧹 PR title prefixes

- `feat:` new functionality
- `fix:` bug fix
- `refactor:` no behavior change, code structure only
- `test:` adding/updating tests
- `chore:` build, deps, tooling
- `docs:` doc-only changes
- `perf:` performance improvement

Match the title prefix to the actual diff. A `refactor:` PR that adds new behavior is mislabeled.

## 🔎 Pre-PR self-check

Before opening or updating a PR, run this checklist:

- [ ] `git diff --stat origin/main..HEAD` matches the PR scope (1-2 concerns max)
- [ ] No `commit_message.txt`, `rewrite_tests.py`, `.Jules/` in diff
- [ ] No unrelated test-file blank-line / import-only churn
- [ ] Title prefix matches the change type
- [ ] CodeRabbit findings addressed or explicitly skipped with reason

## 📂 Where to record learnings

- `.jules/bolt.md` — general engineering learnings (lowercase `j`)
- `.jules/sentinel.md` — security incidents and prevention
- `.jules/palette.md` — UI/UX/design learnings (lowercase, not `.Jules/`)

## 🆘 If you're stuck

Ask in a PR comment instead of force-pushing junk. Maintainer responds faster than CI does to a 40-file PR.
