# Architecture

ApplyMind is a modular monolith: FastAPI HTTP API, Celery workers, React SPA, PostgreSQL (+ pgvector), Redis.

```mermaid
flowchart TB
  subgraph client [apps/web]
    UI[React dashboard CZ]
  end
  subgraph api [apps/api]
    FastAPI[FastAPI]
    Modules[discovery matching rag applications email analytics automation]
    Workers[Celery]
  end
  subgraph data [Infrastructure]
    PG[(PostgreSQL pgvector)]
    Redis[(Redis)]
    Files[Local files]
  end
  UI -->|cookie session| FastAPI
  FastAPI --> Modules
  Modules --> PG
  Modules --> Files
  Workers --> Redis
  Workers --> Modules
```

## Modules

| Module | Responsibility |
|--------|----------------|
| discovery | ATS adapters, RSS, manual import, source health |
| matching | Explainable weighted scoring + hard exclusions |
| rag | Ingestion, embeddings, hybrid retrieval, citations |
| applications | Draft generation, state machine, ApplyRouter, submit |
| email | IMAP/SMTP Email.cz, classification, sync |
| analytics | KPIs and funnel from live tables |
| automation | Celery schedules and manual runs |

## Design constraints

- Single-user (no multi-tenant)
- Human approval for outbound high-impact actions
- Untrusted external content never overrides system prompts
- Czech portals without verified public candidate APIs are marked UNSUPPORTED
