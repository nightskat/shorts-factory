## 2025-02-23 - Prevent SSRF in Media Downloads
**Vulnerability:** Found `urllib.request.urlretrieve` downloading video URLs directly from the Pexels API in `shorts/nodes/clips.py` without verifying the URL scheme first.
**Learning:** Even when consuming seemingly trustworthy 3rd-party APIs, their returned URLs shouldn't be blindly loaded via `urlretrieve`, since it naturally resolves protocols like `file://` or `ftp://` which can lead to Local File Inclusion or Server-Side Request Forgery if the API behaves maliciously or is compromised.
**Prevention:** Always validate URL schemes explicitly via `urllib.parse.urlparse` before processing them in download or network functions, rejecting schemes other than `http` and `https`.
