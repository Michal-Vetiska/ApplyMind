"""Celery task implementations for discovery, matching, email, and analytics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SyncSessionLocal
from app.models.analytics import AutomationRun
from app.models.application import Application, FollowUp
from app.models.email import EmailAccount
from app.models.job import Job, JobSource
from app.models.profile import SearchProfile
from app.modules.discovery.registry import get_adapter
from app.modules.matching.engine import MatchingEngine
from app.services.normalize import normalize_job
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def _finish_run(
    session,
    run_id: str | None,
    *,
    status: str,
    processed: int = 0,
    success: int = 0,
    errors: int = 0,
    log_event: dict | None = None,
) -> None:
    if not run_id:
        return
    run = session.get(AutomationRun, run_id)
    if run is None:
        return
    run.status = status
    run.completed_at = datetime.now(UTC)
    run.processed_count = processed
    run.success_count = success
    run.error_count = errors
    logs = list(run.logs or [])
    if log_event:
        logs.append(log_event)
    run.logs = logs


def _upsert_job_sync(session, source: JobSource, discovered: Any) -> None:
    from app.models.job import Company
    from app.services.dedup import normalize_company_name

    company = None
    if discovered.company_name:
        normalized_name = normalize_company_name(discovered.company_name)
        company = (
            session.execute(select(Company).where(Company.normalized_name == normalized_name))
            .scalars()
            .first()
        )
        if company is None:
            company = Company(name=discovered.company_name, normalized_name=normalized_name)
            session.add(company)
            session.flush()

    normalized = normalize_job(
        title=discovered.title,
        company_name=discovered.company_name,
        description_html=discovered.description_html,
        description_text=discovered.description_text,
        location=discovered.location,
        salary_text=discovered.salary_text,
        technologies_hint=discovered.technologies,
        remote_type=discovered.remote_type,
        employment_type=discovered.employment_type,
    )
    salary = normalized.salary
    job = (
        session.execute(
            select(Job).where(
                Job.source_id == source.id,
                Job.external_id == discovered.external_id,
            )
        )
        .scalars()
        .first()
    )
    fields = {
        "title": normalized.title,
        "normalized_title": normalized.normalized_title,
        "description": normalized.description_text,
        "normalized_description": normalized.description_text,
        "requirements_json": normalized.requirements,
        "location": normalized.location,
        "remote_type": normalized.remote_type,
        "employment_type": normalized.employment_type,
        "seniority": normalized.seniority,
        "salary_min": salary.salary_min if salary else None,
        "salary_max": salary.salary_max if salary else None,
        "currency": salary.currency if salary else None,
        "salary_period": (
            salary.salary_period if salary and salary.salary_period != "unknown" else None
        ),
        "original_salary_text": salary.original_salary_text if salary else None,
        "salary_flag": salary.salary_flag if salary else "SALARY_UNKNOWN",
        "technologies": normalized.technologies,
        "published_at": discovered.published_at,
        "source_url": discovered.source_url,
        "apply_url": discovered.apply_url,
        "contact_email": discovered.contact_email,
        "apply_method": (discovered.apply_capabilities.methods or ["MANUAL_EXTERNAL"])[0],
        "apply_capabilities": discovered.apply_capabilities.model_dump(),
        "content_hash": normalized.content_hash,
        "raw_payload": discovered.raw_payload,
        "company_id": company.id if company else None,
        "deleted_at": None,
    }
    if job is None:
        session.add(
            Job(
                external_id=discovered.external_id,
                source_id=source.id,
                status="DISCOVERED",
                **fields,
            )
        )
    else:
        for key, value in fields.items():
            setattr(job, key, value)


@celery_app.task(name="app.workers.tasks.discover_jobs", bind=True, max_retries=3)
def discover_jobs(self, run_id: str | None = None) -> dict:
    processed = success = errors = 0
    with SyncSessionLocal() as session:
        sources = (
            session.execute(select(JobSource).where(JobSource.enabled.is_(True))).scalars().all()
        )
        for source in sources:
            processed += 1
            source.last_checked_at = datetime.now(UTC)
            try:
                adapter = get_adapter(source.provider, source.configuration)
                if adapter.support_level == "UNSUPPORTED":
                    source.health_status = "UNSUPPORTED"
                    continue
                # Adapters are async — run via asyncio
                import asyncio

                jobs = asyncio.run(adapter.list_jobs())
                for discovered in jobs:
                    _upsert_job_sync(session, source, discovered)
                source.last_success_at = datetime.now(UTC)
                source.health_status = "OK"
                source.last_error = None
                source.discovered_jobs_count = (source.discovered_jobs_count or 0) + len(jobs)
                success += 1
            except Exception as exc:
                errors += 1
                source.health_status = "ERROR"
                source.last_error = str(exc)
                logger.warning("discover_failed", source_id=source.id, error=str(exc))
        _finish_run(
            session,
            run_id,
            status="COMPLETED" if errors == 0 else "COMPLETED_WITH_ERRORS",
            processed=processed,
            success=success,
            errors=errors,
        )
        session.commit()
    # Chain normalize + evaluate
    normalize_jobs.delay()
    evaluate_jobs.delay()
    return {"processed": processed, "success": success, "errors": errors}


@celery_app.task(name="app.workers.tasks.normalize_jobs")
def normalize_jobs(run_id: str | None = None) -> dict:
    count = 0
    with SyncSessionLocal() as session:
        jobs = (
            session.execute(
                select(Job).where(Job.deleted_at.is_(None), Job.normalized_description.is_(None))
            )
            .scalars()
            .all()
        )
        for job in jobs:
            company_name = None
            if job.company_id:
                from app.models.job import Company

                company = session.get(Company, job.company_id)
                company_name = company.name if company else None
            normalized = normalize_job(
                title=job.title,
                company_name=company_name,
                description_html=None,
                description_text=job.description,
                location=job.location,
                salary_text=job.original_salary_text,
                technologies_hint=list(job.technologies or []),
                remote_type=job.remote_type,
                employment_type=job.employment_type,
                seniority=job.seniority,
            )
            job.normalized_title = normalized.normalized_title
            job.normalized_description = normalized.description_text
            job.technologies = normalized.technologies
            job.seniority = normalized.seniority
            job.remote_type = normalized.remote_type
            job.employment_type = normalized.employment_type
            job.content_hash = normalized.content_hash
            job.requirements_json = normalized.requirements
            if normalized.salary:
                job.salary_min = normalized.salary.salary_min
                job.salary_max = normalized.salary.salary_max
                job.currency = normalized.salary.currency
                job.salary_flag = normalized.salary.salary_flag
            count += 1
        _finish_run(session, run_id, status="COMPLETED", processed=count, success=count)
        session.commit()
    deduplicate_jobs.delay()
    return {"normalized": count}


@celery_app.task(name="app.workers.tasks.deduplicate_jobs")
def deduplicate_jobs(run_id: str | None = None) -> dict:
    """Soft-delete later duplicates sharing content_hash within same company+title."""
    removed = 0
    with SyncSessionLocal() as session:
        jobs = (
            session.execute(
                select(Job)
                .where(Job.deleted_at.is_(None), Job.content_hash.is_not(None))
                .order_by(Job.discovered_at.asc())
            )
            .scalars()
            .all()
        )
        seen: dict[str, str] = {}
        for job in jobs:
            key = f"{job.company_id or ''}:{job.normalized_title or ''}:{job.content_hash}"
            if key in seen:
                job.deleted_at = datetime.now(UTC)
                removed += 1
            else:
                seen[key] = job.id
        _finish_run(session, run_id, status="COMPLETED", processed=len(jobs), success=removed)
        session.commit()
    return {"removed": removed}


@celery_app.task(name="app.workers.tasks.evaluate_jobs")
def evaluate_jobs(run_id: str | None = None) -> dict:
    from app.models.job import JobMatch

    scored = 0
    with SyncSessionLocal() as session:
        profiles = (
            session.execute(select(SearchProfile).where(SearchProfile.enabled.is_(True)))
            .scalars()
            .all()
        )
        jobs = session.execute(select(Job).where(Job.deleted_at.is_(None))).scalars().all()
        for profile in profiles:
            engine = MatchingEngine.from_search_profile(profile)
            for job in jobs:
                result = engine.evaluate(profile, job)
                match = (
                    session.execute(
                        select(JobMatch).where(
                            JobMatch.job_id == job.id,
                            JobMatch.search_profile_id == profile.id,
                        )
                    )
                    .scalars()
                    .first()
                )
                values = {
                    "overall_score": result.overall_score,
                    "skill_score": result.skill_score,
                    "seniority_score": result.seniority_score,
                    "location_score": result.location_score,
                    "compensation_score": result.compensation_score,
                    "other_score": result.other_score,
                    "decision": result.decision,
                    "explanation_json": result.explanation,
                    "missing_skills_json": result.missing_skills,
                    "evidence_json": result.evidence,
                    "rule_score": result.overall_score,
                    "evaluated_at": datetime.now(UTC),
                }
                if match is None:
                    session.add(
                        JobMatch(job_id=job.id, search_profile_id=profile.id, **values)
                    )
                else:
                    for k, v in values.items():
                        setattr(match, k, v)
                if result.decision == "SHORTLIST" and job.status in {
                    "DISCOVERED",
                    "MATCHED",
                }:
                    job.status = "SHORTLISTED"
                elif result.decision != "EXCLUDE" and job.status == "DISCOVERED":
                    job.status = "MATCHED"
                scored += 1
        _finish_run(session, run_id, status="COMPLETED", processed=scored, success=scored)
        session.commit()
    return {"scored": scored}


@celery_app.task(name="app.workers.tasks.generate_applications")
def generate_applications(run_id: str | None = None) -> dict:
    """Placeholder draft generation trigger — actual LLM draft via API endpoint."""
    with SyncSessionLocal() as session:
        _finish_run(
            session,
            run_id,
            status="COMPLETED",
            processed=0,
            success=0,
            log_event={
                "event": "noop",
                "detail": "Use POST /api/applications/generate for drafts",
                "at": datetime.now(UTC).isoformat(),
            },
        )
        session.commit()
    return {"generated": 0}


@celery_app.task(name="app.workers.tasks.sync_inbox", bind=True, max_retries=3)
def sync_inbox(self, run_id: str | None = None) -> dict:
    import asyncio

    from app.modules.email.sync import sync_account

    total_created = 0
    with SyncSessionLocal() as session:
        accounts = (
            session.execute(select(EmailAccount).where(EmailAccount.imap_enabled.is_(True)))
            .scalars()
            .all()
        )
        errors = 0
        for account in accounts:
            try:
                # sync_account is async and expects AsyncSession — use a simplified sync path
                from app.core.security import decrypt_secret
                from app.modules.email.classifier import classify_email
                from app.modules.email.imap_client import IMAPClient
                from app.models.email import EmailMessage

                password = decrypt_secret(account.encrypted_credentials)
                with IMAPClient(
                    host=account.imap_host,
                    port=account.imap_port,
                    username=account.email_address,
                    password=password,
                ) as client:
                    account.folders_json = client.list_folders()
                    messages = client.fetch_messages("INBOX", limit=50)
                for msg in messages:
                    exists = (
                        session.execute(
                            select(EmailMessage).where(
                                EmailMessage.account_id == account.id,
                                EmailMessage.message_id == msg.message_id,
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if exists:
                        continue
                    classification = classify_email(
                        subject=msg.subject, text_body=msg.text_body, sender=msg.sender
                    )
                    session.add(
                        EmailMessage(
                            account_id=account.id,
                            message_id=msg.message_id,
                            in_reply_to=msg.in_reply_to,
                            references_header=msg.references,
                            thread_identifier=msg.in_reply_to or msg.message_id,
                            sender=msg.sender,
                            recipients=msg.recipients,
                            subject=msg.subject,
                            text_body=msg.text_body,
                            html_body=msg.html_body,
                            received_at=msg.received_at,
                            classification=classification.classification,
                            classification_confidence=classification.confidence,
                            folder=msg.folder,
                            attachment_metadata=msg.attachment_metadata,
                        )
                    )
                    total_created += 1
                account.last_sync_at = datetime.now(UTC)
                account.connected = True
            except Exception as exc:
                errors += 1
                account.connected = False
                logger.warning("inbox_sync_failed", error=str(exc))
        _finish_run(
            session,
            run_id,
            status="COMPLETED" if errors == 0 else "COMPLETED_WITH_ERRORS",
            processed=len(accounts),
            success=len(accounts) - errors,
            errors=errors,
        )
        session.commit()
    classify_responses.delay()
    return {"created": total_created}


@celery_app.task(name="app.workers.tasks.classify_responses")
def classify_responses(run_id: str | None = None) -> dict:
    from app.models.email import EmailMessage
    from app.modules.email.classifier import classify_email

    updated = 0
    with SyncSessionLocal() as session:
        messages = (
            session.execute(
                select(EmailMessage).where(EmailMessage.classification == "UNCERTAIN")
            )
            .scalars()
            .all()
        )
        for msg in messages:
            result = classify_email(
                subject=msg.subject, text_body=msg.text_body, sender=msg.sender
            )
            if result.classification != "UNCERTAIN":
                msg.classification = result.classification
                msg.classification_confidence = result.confidence
                updated += 1
        _finish_run(session, run_id, status="COMPLETED", processed=len(messages), success=updated)
        session.commit()
    return {"updated": updated}


@celery_app.task(name="app.workers.tasks.suggest_followups")
def suggest_followups(run_id: str | None = None) -> dict:
    suggested = 0
    cutoff = datetime.now(UTC) - timedelta(days=7)
    with SyncSessionLocal() as session:
        apps = (
            session.execute(
                select(Application).where(
                    Application.status.in_(["SENT_UNCONFIRMED", "SUBMITTED"]),
                    Application.sent_at.is_not(None),
                    Application.sent_at <= cutoff,
                )
            )
            .scalars()
            .all()
        )
        for app in apps:
            existing = (
                session.execute(
                    select(FollowUp).where(
                        FollowUp.application_id == app.id,
                        FollowUp.status.in_(["SUGGESTED", "SCHEDULED", "SENT"]),
                    )
                )
                .scalars()
                .first()
            )
            if existing:
                continue
            session.add(
                FollowUp(
                    application_id=app.id,
                    status="SUGGESTED",
                    generated_message=None,
                )
            )
            suggested += 1
        _finish_run(session, run_id, status="COMPLETED", processed=len(apps), success=suggested)
        session.commit()
    return {"suggested": suggested}


@celery_app.task(name="app.workers.tasks.refresh_source_health")
def refresh_source_health(run_id: str | None = None) -> dict:
    import asyncio

    checked = 0
    with SyncSessionLocal() as session:
        sources = session.execute(select(JobSource)).scalars().all()
        for source in sources:
            checked += 1
            try:
                adapter = get_adapter(source.provider, source.configuration)
                result = asyncio.run(adapter.health_check())
                source.health_status = str(result.get("status") or "UNKNOWN")
                source.last_checked_at = datetime.now(UTC)
                if result.get("error"):
                    source.last_error = str(result["error"])
            except Exception as exc:
                source.health_status = "ERROR"
                source.last_error = str(exc)
        _finish_run(session, run_id, status="COMPLETED", processed=checked, success=checked)
        session.commit()
    return {"checked": checked}


@celery_app.task(name="app.workers.tasks.update_analytics")
def update_analytics(run_id: str | None = None) -> dict:
    with SyncSessionLocal() as session:
        job_count = len(session.execute(select(Job).where(Job.deleted_at.is_(None))).scalars().all())
        app_count = len(session.execute(select(Application)).scalars().all())
        _finish_run(
            session,
            run_id,
            status="COMPLETED",
            processed=1,
            success=1,
            log_event={
                "event": "snapshot",
                "jobs": job_count,
                "applications": app_count,
                "at": datetime.now(UTC).isoformat(),
            },
        )
        session.commit()
    return {"jobs": job_count, "applications": app_count}
