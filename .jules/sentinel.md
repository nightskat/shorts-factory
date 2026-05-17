## 2026-05-13 - [Fix Timing Attacks and CSRF Bypass]
**Vulnerability:** The application was vulnerable to timing attacks when verifying login and session tokens because it used standard string inequality (`!=`). Additionally, the CSRF token validation did not check if the token matched the current user's session, leading to a possible CSRF bypass/fixation.
**Learning:** In Python, standard string comparison operators short-circuit, allowing attackers to measure the time taken for a string comparison to guess secret tokens character by character. For CSRF, a token must be securely bound to the session, otherwise an attacker can generate a valid token from an unauthenticated endpoint and use it to execute authenticated actions.
**Prevention:** Always use `secrets.compare_digest()` for comparing sensitive tokens. Ensure CSRF tokens embed a session identifier and that the validation logic checks this identifier against the active user's session.

## 2026-05-14 - [Missing Security Headers in Web App]
**Vulnerability:** The FastAPI application was not returning standard HTTP security headers, leaving it vulnerable to common client-side attacks like clickjacking, MIME-type sniffing, and failing to enforce HTTPS properly.
**Learning:** Adding a generic `http` middleware in FastAPI is a simple but effective defense-in-depth approach to globally inject security headers into every HTTP response.
**Prevention:** Always include an HTTP middleware or configure the reverse proxy to append headers like `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `X-XSS-Protection`, and `Referrer-Policy`.

## 2026-05-17 - [Fix Server-Side Request Forgery (SSRF) in media fetching]
**Vulnerability:** The `clips` pipeline node fetched video URLs dynamically returned by a provider using `urllib.request.urlretrieve` without validating the URL scheme, enabling an attacker (if they could control the provider response) to force the application to read arbitrary local files via the `file://` scheme or scan internal networks via other implicit schemes.
**Learning:** Functions like `urllib.request.urlretrieve` do not restrict the URL schemes they accept by default. They can implicitly resolve `file://`, `ftp://`, and others, which poses a significant security risk when handling unverified or untrusted URLs.
**Prevention:** Always strictly validate and allowlist the schemes (e.g., `http://`, `https://`) of any dynamically generated or untrusted URL before passing it to network fetching functions to prevent SSRF and local file reads.
