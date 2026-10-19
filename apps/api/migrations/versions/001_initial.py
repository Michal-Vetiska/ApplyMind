"""Initial schema: all ApplyMind tables + pgvector extension.

Revision ID: 001_initial
Revises:
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "user_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)

    op.create_table(
        "session_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
    op.create_index("ix_session_tokens_token_hash", "session_tokens", ["token_hash"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("portfolio_url", sa.String(512), nullable=True),
        sa.Column("github_url", sa.String(512), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("technologies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("experience", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("education", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("languages", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("portfolio_projects", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferred_application_language", sa.String(8), nullable=False, server_default="cs"),
        sa.Column("tone_preference", sa.String(64), nullable=False, server_default="professional_concise"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "search_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("locations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("job_titles", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("technologies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("employment_types", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("remote_preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("minimum_salary", sa.Integer(), nullable=True),
        sa.Column("preferred_salary_min", sa.Integer(), nullable=True),
        sa.Column("preferred_salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(8), nullable=False, server_default="CZK"),
        sa.Column("hourly_rate_min", sa.Float(), nullable=True),
        sa.Column("seniority", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("exclusion_rules", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("matching_threshold", sa.Float(), nullable=False, server_default="60.0"),
        sa.Column("auto_apply_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("weight_technology", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("weight_seniority", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("weight_location", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("weight_compensation", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("weight_other", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_hash", sa.String(128), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False, server_default="application/pdf"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("target_roles", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("poll_interval_minutes", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health_status", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("discovered_jobs_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_sources_provider", "job_sources", ["provider"])

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("briefing", sa.Text(), nullable=True),
        sa.Column("intelligence_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])
    op.create_index("ix_companies_domain", "companies", ["domain"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("normalized_title", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("requirements_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote_type", sa.String(64), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("seniority", sa.String(64), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("salary_period", sa.String(32), nullable=True),
        sa.Column("original_salary_text", sa.Text(), nullable=True),
        sa.Column("salary_flag", sa.String(32), nullable=False, server_default="SALARY_UNKNOWN"),
        sa.Column("technologies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("apply_url", sa.String(1024), nullable=True),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("apply_method", sa.String(64), nullable=False, server_default="MANUAL_EXTERNAL"),
        sa.Column("apply_capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(64), nullable=False, server_default="DISCOVERED"),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_jobs_source_external"),
    )
    op.create_index("ix_jobs_content_hash", "jobs", ["content_hash"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("search_profile_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("search_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("skill_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("seniority_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("location_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("compensation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("other_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(32), nullable=False, server_default="REVIEW"),
        sa.Column("explanation_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("missing_skills_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rule_score", sa.Float(), nullable=True),
        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column("llm_score", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "search_profile_id", name="uq_job_matches_job_profile"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_search_profile_id", "job_matches", ["search_profile_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False, server_default="upload"),
        sa.Column("scope", sa.String(64), nullable=False, server_default="PERSONAL_KNOWLEDGE"),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section_heading", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_fts "
        "ON knowledge_chunks USING gin (to_tsvector('simple', content))"
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="DRAFTED"),
        sa.Column("apply_method", sa.String(64), nullable=False, server_default="EMAIL_APPROVAL_REQUIRED"),
        sa.Column("generated_subject", sa.String(512), nullable=True),
        sa.Column("generated_message", sa.Text(), nullable=True),
        sa.Column("approved_message", sa.Text(), nullable=True),
        sa.Column("approved_subject", sa.String(512), nullable=True),
        sa.Column("recipient_email", sa.String(320), nullable=True),
        sa.Column("external_application_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="cs"),
        sa.Column("matching_explanation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generation_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("submission_logs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_applications_idempotency"),
    )
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "application_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("knowledge_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_evidence_application_id", "application_evidence", ["application_id"])

    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("suggested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUGGESTED"),
        sa.Column("generated_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_follow_ups_application_id", "follow_ups", ["application_id"])

    op.create_table(
        "email_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False, server_default="email.cz"),
        sa.Column("email_address", sa.String(320), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("imap_host", sa.String(255), nullable=False, server_default="imap.seznam.cz"),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("smtp_host", sa.String(255), nullable=False, server_default="smtp.seznam.cz"),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="465"),
        sa.Column("imap_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("smtp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("folders_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("allow_llm_processing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email_address", name="uq_email_accounts_email_address"),
    )

    op.create_table(
        "email_messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.String(512), nullable=False),
        sa.Column("in_reply_to", sa.String(512), nullable=True),
        sa.Column("references_header", sa.Text(), nullable=True),
        sa.Column("thread_identifier", sa.String(512), nullable=True),
        sa.Column("sender", sa.String(512), nullable=False),
        sa.Column("recipients", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("subject", sa.String(1024), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("classification", sa.String(64), nullable=False, server_default="UNCERTAIN"),
        sa.Column("classification_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("related_application_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("association_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("folder", sa.String(255), nullable=True),
        sa.Column("attachment_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "message_id", name="uq_email_messages_account_msgid"),
    )
    op.create_index("ix_email_messages_account_id", "email_messages", ["account_id"])
    op.create_index("ix_email_messages_thread_identifier", "email_messages", ["thread_identifier"])

    op.create_table(
        "automation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("job_type", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="RUNNING"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_automation_runs_job_type", "automation_runs", ["job_type"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(128), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_llm_usage_operation", "llm_usage", ["operation"])
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])

    op.create_table(
        "app_settings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", name="uq_app_settings_key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("llm_usage")
    op.drop_table("audit_logs")
    op.drop_table("automation_runs")
    op.drop_table("email_messages")
    op.drop_table("email_accounts")
    op.drop_table("follow_ups")
    op.drop_table("application_evidence")
    op.drop_table("applications")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_content_fts")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("job_matches")
    op.drop_table("jobs")
    op.drop_table("companies")
    op.drop_table("job_sources")
    op.drop_table("resumes")
    op.drop_table("search_profiles")
    op.drop_table("user_profiles")
    op.drop_table("session_tokens")
    op.drop_table("user_accounts")
