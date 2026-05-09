# Scaffold Fix Plan (Post-Adversarial Review)

**Goal:** Resolve P0 and P1 vulnerabilities identified by Codex Hub in the scaffold.

---

### Task 1: Path Robustness (P0)
**Files:** `shorts/config.py`
- Change `DATA_DIR` and other paths to allow env overrides.

### Task 2: Lease Data Type (P1)
**Files:** `shorts/db.py`
- Change `lease_heartbeat_at` from `DATETIME` to `INTEGER` (Unix epoch).

### Task 3: Execution Context Hardening (P1)
**Files:** `shorts/config.py`
- Update `snapshot_execution_context` to capture more environment variables (models, temperatures, etc.).

### Task 4: Lease Utility (P2)
**Files:** `shorts/utils/lease.py`
- Add `get_lease_owner()` helper.
