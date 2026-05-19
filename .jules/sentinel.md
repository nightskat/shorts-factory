## 2026-05-13 - [Fix Timing Attacks and CSRF Bypass]
**Vulnerability:** The application was vulnerable to timing attacks when verifying login and session tokens because it used standard string inequality (`!=`). Additionally, the CSRF token validation did not check if the token matched the current user's session, leading to a possible CSRF bypass/fixation.
**Learning:** In Python, standard string comparison operators short-circuit, allowing attackers to measure the time taken for a string comparison to guess secret tokens character by character. For CSRF, a token must be securely bound to the session, otherwise an attacker can generate a valid token from an unauthenticated endpoint and use it to execute authenticated actions.
**Prevention:** Always use `secrets.compare_digest()` for comparing sensitive tokens. Ensure CSRF tokens embed a session identifier and that the validation logic checks this identifier against the active user's session.

## 2026-05-14 - [Missing Security Headers in Web App]
**Vulnerability:** The FastAPI application was not returning standard HTTP security headers, leaving it vulnerable to common client-side attacks like clickjacking, MIME-type sniffing, and failing to enforce HTTPS properly.
**Learning:** Adding a generic `http` middleware in FastAPI is a simple but effective defense-in-depth approach to globally inject security headers into every HTTP response.
**Prevention:** Always include an HTTP middleware or configure the reverse proxy to append headers like `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `X-XSS-Protection`, and `Referrer-Policy`.

## 2024-05-19 - SSRF Vulnerability in Media Downloading
**Vulnerability:** Server-Side Request Forgery (SSRF) and arbitrary local file read vulnerability in `shorts/nodes/clips.py` due to passing an unvalidated URL from an external provider (Pexels) directly to `urllib.request.urlretrieve`. If an attacker or a compromised external API returned a `file://` URL, it could be used to read arbitrary files from the local filesystem.
**Learning:** `urllib.request.urlretrieve` supports multiple schemes, including `file://`. When downloading media based on URLs provided by external sources, even seemingly trusted ones, the scheme must be strictly validated to prevent SSRF and local file access.
**Prevention:** Always parse URLs using `urllib.parse.urlparse` and explicitly allowlist safe schemes (e.g., `http` and `https`) before downloading files or making external requests.
