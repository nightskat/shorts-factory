🎯 **What:** The `run` function in `shorts/nodes/upload_yt.py` was refactored into smaller, logically focused helper functions.

💡 **Why:** Breaking down the long function improves readability, testability, and maintainability. Each helper function now encapsulates a specific step of the YouTube upload process, such as getting render output paths, checking idempotency records, and updating the database state.

✅ **Verification:** I ran `ruff check` and the full test suite (`python -m pytest`). All 119 active tests successfully pass, including the specific unit tests for `upload_yt.py`. I confirmed that the original logic and safety constraints (like the idempotency check and proper SQLite connections) were strictly preserved.

✨ **Result:** A much cleaner `run` function that clearly outlines the two-phase upload protocol, improving long-term codebase health.
