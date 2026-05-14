## 2026-05-14 - Test Improvement for Voice Examples

**Learning:** Testing functions that hardcode database initialization (via module-level properties like `config.DB_PATH`) requires careful mocking. The test setup must ensure the schema is initialized cleanly and patched using `monkeypatch` to redirect execution safely to a temporary file. Testing `get_top_examples()` behavior requires verifying determinism based on creation dates, sources, and limits rather than simply counting records.

**Action:** Whenever introducing new tests for db wrappers, continue using a `monkeypatch` plus `tmp_path` setup instead of attempting to overwrite global constants. Make sure to execute `SCHEMA` inside the mocked db to maintain functional equivalence to production db initialization.
