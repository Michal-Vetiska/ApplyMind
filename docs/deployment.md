# Deployment

Recommended local/prod-like path: Docker Compose (`db`, `redis`, `api`, `worker`, `web`).

```bash
docker compose up --build
```

For a personal VPS:

1. Reverse proxy (Caddy/Nginx) with TLS
2. Restrict CORS origins
3. Rotate `SECRET_KEY` and `SECRET_ENCRYPTION_KEY`
4. Keep `EMAIL_SENDING_ENABLED=false` until verified
5. Persist `data/` volume for resumes/knowledge files
6. Run Celery worker+beat for scheduled discovery/inbox sync

Kubernetes is intentionally out of scope.
