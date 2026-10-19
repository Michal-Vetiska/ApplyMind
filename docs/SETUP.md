# Setup

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (or Colima) for Postgres + Redis

## Environment

```bash
cp .env.example .env
```

Important variables:

| Variable | Purpose |
|----------|---------|
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded login |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | Async + sync SQLAlchemy URLs |
| `REDIS_URL` | Celery broker |
| `LLM_API_KEY` / `LLM_BASE_URL` | OpenAI-compatible provider |
| `EMAIL_DRY_RUN` / `EMAIL_SENDING_ENABLED` | Outbound safety switches |
| `SECRET_KEY` / `SECRET_ENCRYPTION_KEY` | Sessions + Fernet secret encryption |

## Database

```bash
docker compose up -d db redis
cd apps/api && source .venv/bin/activate
alembic upgrade head
```

## API

```bash
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

OpenAPI: http://localhost:8000/api/docs

## Web

```bash
cd apps/web && npm install && npm run dev
```

Vite proxies `/api` to port 8000.

## Email.cz

1. Create an application password in Seznam account settings if required.
2. In Nastavení, connect IMAP (`imap.seznam.cz:993`) / SMTP (`smtp.seznam.cz:465`).
3. Keep dry-run enabled until you intentionally turn on sending.
