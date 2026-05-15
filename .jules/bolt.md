## 2025-02-27 - FastAPI Event Loop Blocking with Synchronous DB Queries
**Learning:** In FastAPI applications, defining route handlers with `async def` makes them run directly on the main asyncio event loop thread. If these handlers contain synchronous blocking operations like `sqlite3.connect` and `conn.execute`, they will block the entire event loop, causing severe latency degradation for all concurrent requests.
**Action:** Always define endpoints that perform synchronous DB queries as standard `def` rather than `async def`. FastAPI automatically provisions an external threadpool for `def` functions. If an endpoint must be `async def` (e.g., to `await request.json()`), explicitly offload the blocking synchronous parts using `asyncio.to_thread`.
## 2024-05-14 - Refactoring Long Functions with Explicit Type Checking
**Learning:** When refactoring functions that originally relied on truthy/falsy implicit checks for variables that could be empty (e.g. empty strings like `script_content` or empty lists), explicitly check `is None` to avoid unintended bugs when empty values are valid returns.
**Action:** Always verify edge cases like empty strings/lists during extraction, especially when type hints are explicitly `str | None` or `list | None`.

## 2025-05-15 - Jinja2 Template Dictionary Lookups and Iterations
**Learning:** In Jinja2 templates, looking up values using `dict.get(key1, {}).get(key2)` within a loop over jobs implies the backend should provide a properly nested dictionary structure (`{job_id: {step_name: result}}`). Supplying a flat list of dicts to the template causes these lookups to fail silently or throw errors, breaking the UI rendering.
**Action:** When fetching flat row results from SQLite that will be accessed by multiple keys in the template, pre-process and group the data into nested dictionaries (O(1) lookups) in the endpoint handler before passing it to the template context.
