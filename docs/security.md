# Security

- Single-user session cookies (HTTP-only, SameSite=Lax)
- Argon2 password hashing
- Fernet encryption for email credentials at rest
- CORS allowlist from env
- Upload type/size limits
- Secrets never returned by API
- External HTML sanitized; retrieved content treated as untrusted data
- Default dry-run for outbound email
- Audit log for auth, imports, generation, sync events

Do not expose the app publicly without changing defaults and hardening TLS/proxy.
