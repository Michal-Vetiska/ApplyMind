# ApplyMind

RAG-powered personal job search and application agent for a single user.

ApplyMind discovers roles from supported public ATS boards, normalizes postings, scores fit with explainable matching, retrieves approved personal evidence via hybrid RAG, drafts applications with citation tracking, and manages email/inbox workflows with human-in-the-loop sending.

## Status matrix

| Area | Status |
|------|--------|
| Greenhouse / Lever / Ashby / SmartRecruiters discovery | **Implemented** (public GET per company board) |
| RSS / manual URL import | **Implemented** |
| Jobs.cz / Práce.cz / StartupJobs marketplace / Webtrh auto-discovery | **Unsupported** (no verified public candidate API; use manual import / email alerts) |
| ATS API application POST | **Unavailable** without employer credentials — use hosted form / assisted flow |
| Explainable matching | **Implemented** |
| RAG hybrid retrieval (pgvector + FTS + RRF) | **Implemented** (embeddings require LLM API key) |
| Application generation | **Implemented** (template fallback without LLM; LLM when configured) |
| Email.cz IMAP/SMTP | **Implemented** (credentials encrypted at rest; dry-run send by default) |
| Playwright form assist | **Experimental** |
| Analytics from live DB | **Implemented** |
| Multi-tenant / billing | **Not in scope** |

## Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Celery, Redis
- **Database:** PostgreSQL + pgvector
- **AI:** OpenAI-compatible chat + embeddings interface

## Quick start

```bash
cp .env.example .env
# edit ADMIN_PASSWORD, optionally LLM_API_KEY

# Start Postgres + Redis (requires Docker / Colima)
docker compose up -d db redis

cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173 — login with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`.

Default local credentials after seed:

- Email: `admin@example.com`
- Password: `changeme`

## Core workflow

1. Edit profile and search preferences (Nastavení) — seed data is **not** verified evidence until approved.
2. Upload resume / knowledge documents and **approve** facts before generation uses them.
3. Add ATS sources (board tokens / site slugs) under Zdroje, or import a job URL manually.
4. Evaluate matches, generate a draft, review citations, approve, then submit (dry-run until you enable SMTP).

## Safety defaults

- `EMAIL_DRY_RUN=true` and `EMAIL_SENDING_ENABLED=false`
- Automatic apply disabled on search profiles
- Unapproved experience is not treated as verified evidence
- Czech portal scrapers are not implemented

## Documentation

- [Architecture](docs/architecture.md)
- [Setup](docs/SETUP.md)
- [Integrations](docs/integrations.md)
- [RAG](docs/rag.md)
- [Security](docs/security.md)
- [Evaluation](docs/evaluation.md)
- [Deployment](docs/deployment.md)

## Tests

```bash
cd apps/api && source .venv/bin/activate && pytest -q
cd apps/web && npm test && npm run typecheck
```

## License

MIT — see [LICENSE](LICENSE).
