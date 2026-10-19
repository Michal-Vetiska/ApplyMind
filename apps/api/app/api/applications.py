"""Application lifecycle endpoints."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.session import get_db
from app.models.application import Application, ApplicationEvidence
from app.models.auth import UserAccount
from app.models.email import EmailAccount
from app.models.job import Job
from app.models.profile import Resume, SearchProfile, UserProfile
from app.modules.applications.generator import GenerationContext, generate_application
from app.modules.applications.router import ApplyRouter
from app.modules.applications.state_machine import can_transition, transition
from app.modules.email.smtp_client import SMTPClient
from app.schemas.applications import (
    ApproveApplicationRequest,
    ApplicationOut,
    GenerateApplicationRequest,
    SubmitApplicationRequest,
    TransitionRequest,
)
from app.schemas.common import MessageOut, Paginated
from app.services.audit import record_audit

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _idempotency_key(job_id: str, resume_id: str | None) -> str:
    raw = f"{job_id}:{resume_id or 'default'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.get("", response_model=Paginated[ApplicationOut])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = None,
) -> Paginated[ApplicationOut]:
    stmt = select(Application).options(selectinload(Application.evidence))
    count_stmt = select(func.count()).select_from(Application)
    if status:
        stmt = stmt.where(Application.status == status)
        count_stmt = count_stmt.where(Application.status == status)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    result = await db.execute(
        stmt.order_by(Application.last_activity_at.desc()).offset(offset).limit(limit)
    )
    return Paginated(items=list(result.scalars().all()), total=total, limit=limit, offset=offset)


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Application:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evidence))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.post("/generate", response_model=ApplicationOut, status_code=201)
async def generate(
    payload: GenerateApplicationRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Application:
    job = await db.get(Job, payload.job_id)
    if job is None or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_result = await db.execute(select(UserProfile).limit(1))
    user_profile = profile_result.scalar_one_or_none()

    language = payload.language or (
        user_profile.preferred_application_language if user_profile else "cs"
    )
    company_name = None
    if job.company_id:
        from app.models.job import Company

        company = await db.get(Company, job.company_id)
        company_name = company.name if company else None

    matching_explanation = {}
    if payload.search_profile_id:
        sp = await db.get(SearchProfile, payload.search_profile_id)
        if sp:
            from app.modules.matching.engine import MatchingEngine

            matching_explanation = MatchingEngine.from_search_profile(sp).evaluate(
                sp, job
            ).explanation

    decision = ApplyRouter().decide(
        apply_capabilities=job.apply_capabilities,
        apply_url=job.apply_url,
        contact_email=job.contact_email,
        apply_method_hint=job.apply_method,
    )

    ctx = GenerationContext(
        job_title=job.title,
        company_name=company_name,
        job_description=job.normalized_description or job.description,
        profile_summary=user_profile.summary if user_profile else None,
        profile_technologies=list(user_profile.technologies or []) if user_profile else [],
        tone=user_profile.tone_preference if user_profile else "professional_concise",
        language=language,
        matching_explanation=matching_explanation,
    )
    generated = await generate_application(db, ctx)

    key = _idempotency_key(job.id, payload.resume_id)
    existing = await db.execute(select(Application).where(Application.idempotency_key == key))
    app = existing.scalar_one_or_none()
    if app is None:
        app = Application(
            job_id=job.id,
            resume_id=payload.resume_id,
            idempotency_key=key,
            status="DRAFTED",
            apply_method=decision.method,
            language=language,
        )
        db.add(app)
        await db.flush()
    else:
        if not can_transition(app.status, "DRAFTED") and app.status != "DRAFTED":
            # Allow regenerating from READY_FOR_REVIEW / FAILED via DRAFTED
            if can_transition(app.status, "DRAFTED"):
                app.status = "DRAFTED"
        else:
            app.status = "DRAFTED"

    app.generated_subject = generated.subject
    app.generated_message = generated.message
    app.recipient_email = job.contact_email or decision.contact_email
    app.matching_explanation = matching_explanation
    app.generation_metadata = {
        **generated.metadata,
        "apply_decision": {
            "method": decision.method,
            "reason": decision.reason,
            "dry_run": decision.dry_run,
        },
        "unsupported_claims": generated.unsupported_claims,
    }
    app.last_activity_at = datetime.now(UTC)
    app.apply_method = decision.method

    # Replace evidence rows without lazy IO during flush
    existing_evidence = await db.execute(
        select(ApplicationEvidence).where(ApplicationEvidence.application_id == app.id)
    )
    for row in existing_evidence.scalars().all():
        await db.delete(row)
    await db.flush()
    for claim in generated.claims:
        db.add(
            ApplicationEvidence(
                application_id=app.id,
                claim=claim.claim,
                source_chunk_id=claim.source_chunk_id,
                verification_status=claim.verification_status,
            )
        )

    job.status = "DRAFTED"
    await record_audit(db, "application.generated", "application", app.id, {"job_id": job.id})
    await db.commit()

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evidence))
        .where(Application.id == app.id)
    )
    return result.scalar_one()


@router.post("/{application_id}/approve", response_model=ApplicationOut)
async def approve(
    application_id: str,
    payload: ApproveApplicationRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Application:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evidence))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Move through READY_FOR_REVIEW if needed
    if app.status == "DRAFTED":
        app.status = transition(app.status, "READY_FOR_REVIEW").value
    app.status = transition(app.status, "APPROVED").value
    app.approved_subject = payload.subject or app.generated_subject
    app.approved_message = payload.message or app.generated_message
    if payload.recipient_email:
        app.recipient_email = payload.recipient_email
    app.last_activity_at = datetime.now(UTC)
    await record_audit(db, "application.approved", "application", app.id, {})
    await db.commit()
    await db.refresh(app)
    return app


@router.post("/{application_id}/submit", response_model=ApplicationOut)
async def submit(
    application_id: str,
    payload: SubmitApplicationRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Application:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Submission requires confirm=true")

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evidence))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Application must be APPROVED before submit")

    settings = get_settings()
    app.status = transition(app.status, "SUBMISSION_IN_PROGRESS").value
    app.last_activity_at = datetime.now(UTC)
    logs = list(app.submission_logs or [])

    if app.apply_method in {"EMAIL_DRY_RUN", "EMAIL_APPROVAL_REQUIRED"}:
        account_result = await db.execute(select(EmailAccount).limit(1))
        account = account_result.scalar_one_or_none()
        if account is None:
            # Dry-run without configured mailbox still allowed
            send_result_detail = "No email account configured — recorded as dry-run"
            dry = True
            success = True
            from_addr = "noreply@localhost"
            password = ""
            smtp = None
        else:
            password = decrypt_secret(account.encrypted_credentials)
            from_addr = account.email_address
            smtp = SMTPClient(
                host=account.smtp_host,
                port=account.smtp_port,
                username=account.email_address,
                password=password,
            )

        if not app.recipient_email:
            app.status = transition(app.status, "FAILED", evidence=["missing recipient"]).value
            app.failure_reason = "Missing recipient_email"
            logs.append({"event": "submit_failed", "reason": app.failure_reason})
            app.submission_logs = logs
            await db.commit()
            await db.refresh(app)
            return app

        if smtp is None:
            dry = True
            success = True
            detail = send_result_detail
            message_id = None
        else:
            message = smtp.build_message(
                from_addr=from_addr,
                to_addrs=[app.recipient_email],
                subject=app.approved_subject or app.generated_subject or "Application",
                body_text=app.approved_message or app.generated_message or "",
            )
            send_result = smtp.send(message)
            dry = send_result.dry_run
            success = send_result.success
            detail = send_result.detail
            message_id = send_result.message_id

        logs.append(
            {
                "event": "email_submit",
                "dry_run": dry,
                "success": success,
                "detail": detail,
                "message_id": message_id,
                "at": datetime.now(UTC).isoformat(),
            }
        )
        app.submission_logs = logs
        if success:
            # SMTP accepted != employer received
            next_status = "SENT_UNCONFIRMED" if not dry else "SENT_UNCONFIRMED"
            if dry or settings.email_dry_run:
                next_status = "SENT_UNCONFIRMED"
            app.status = transition(app.status, next_status).value
            app.sent_at = datetime.now(UTC)
            app.failure_reason = None
        else:
            app.status = transition(app.status, "FAILED", evidence=[detail]).value
            app.failure_reason = detail
    elif app.apply_method == "FORM_ASSISTED":
        logs.append(
            {
                "event": "form_assisted_queued",
                "apply_url": (await db.get(Job, app.job_id)).apply_url if app.job_id else None,
                "note": "Open hosted form; Playwright assist stops on CAPTCHA",
                "at": datetime.now(UTC).isoformat(),
            }
        )
        app.submission_logs = logs
        app.status = transition(app.status, "SENT_UNCONFIRMED").value
    elif app.apply_method == "API_AUTHORIZED":
        logs.append(
            {
                "event": "api_unavailable",
                "detail": "API credentials not configured",
                "at": datetime.now(UTC).isoformat(),
            }
        )
        app.submission_logs = logs
        app.status = transition(app.status, "FAILED", evidence=["api unavailable"]).value
        app.failure_reason = "API_AUTHORIZED submit unavailable without employer credentials"
    else:
        logs.append(
            {
                "event": "manual_external",
                "detail": "User must submit externally",
                "at": datetime.now(UTC).isoformat(),
            }
        )
        app.submission_logs = logs
        app.status = transition(app.status, "SENT_UNCONFIRMED").value

    await record_audit(db, "application.submitted", "application", app.id, {"status": app.status})
    await db.commit()
    await db.refresh(app)
    return app


@router.post("/{application_id}/transition", response_model=ApplicationOut)
async def transition_status(
    application_id: str,
    payload: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Application:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.evidence))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    try:
        app.status = transition(app.status, payload.status, evidence=payload.evidence).value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logs = list(app.submission_logs or [])
    logs.append(
        {
            "event": "transition",
            "to": app.status,
            "evidence": payload.evidence,
            "metadata": payload.metadata,
            "at": datetime.now(UTC).isoformat(),
        }
    )
    app.submission_logs = logs
    app.last_activity_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(app)
    return app


@router.delete("/{application_id}", response_model=MessageOut)
async def withdraw(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    app = await db.get(Application, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    try:
        app.status = transition(app.status, "WITHDRAWN").value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    app.last_activity_at = datetime.now(UTC)
    await db.commit()
    return MessageOut(message="Withdrawn")
