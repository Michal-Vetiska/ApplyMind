# Database

PostgreSQL 16 with `vector` extension (pgvector).

Core tables: `user_accounts`, `session_tokens`, `user_profiles`, `search_profiles`, `resumes`, `job_sources`, `companies`, `jobs`, `job_matches`, `knowledge_documents`, `knowledge_chunks`, `applications`, `application_evidence`, `follow_ups`, `email_accounts`, `email_messages`, `automation_runs`, `audit_logs`, `llm_usage`, `app_settings`.

Migrations: `apps/api/migrations` via Alembic.

Dedup keys: `(source_id, external_id)` unique + content hash fingerprint for cross-source duplicates.
