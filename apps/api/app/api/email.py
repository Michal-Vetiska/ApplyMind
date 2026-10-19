"""Email account and message endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.email import EmailAccount, EmailMessage
from app.modules.email.imap_client import IMAPClient
from app.modules.email.smtp_client import SMTPClient
from app.modules.email.sync import sync_account
from app.schemas.common import MessageOut, Paginated
from app.schemas.email import (
    EmailAccountCreate,
    EmailAccountOut,
    EmailMessageOut,
    SyncRequest,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/accounts", response_model=list[EmailAccountOut])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[EmailAccount]:
    result = await db.execute(select(EmailAccount).order_by(EmailAccount.created_at.desc()))
    return list(result.scalars().all())


@router.post("/accounts", response_model=EmailAccountOut, status_code=201)
async def create_account(
    payload: EmailAccountCreate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> EmailAccount:
    account = EmailAccount(
        provider=payload.provider,
        email_address=str(payload.email_address).lower(),
        encrypted_credentials=encrypt_secret(payload.password),
        imap_host=payload.imap_host,
        imap_port=payload.imap_port,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        allow_llm_processing=payload.allow_llm_processing,
        connected=True,
    )
    db.add(account)
    await record_audit(
        db, "email.account_created", "email_account", None, {"email": account.email_address}
    )
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", response_model=MessageOut)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    account = await db.get(EmailAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
    return MessageOut(message="Deleted")


@router.post("/accounts/{account_id}/test")
async def test_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> dict:
    from app.core.security import decrypt_secret

    account = await db.get(EmailAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    password = decrypt_secret(account.encrypted_credentials)
    imap_result: dict = {"ok": False}
    smtp_result: dict = {"ok": False}
    try:
        with IMAPClient(
            host=account.imap_host,
            port=account.imap_port,
            username=account.email_address,
            password=password,
        ) as client:
            imap_result = client.test_connection()
            account.folders_json = imap_result.get("folders") or []
            account.connected = True
    except Exception as exc:
        imap_result = {"ok": False, "error": str(exc)}
        account.connected = False

    smtp = SMTPClient(
        host=account.smtp_host,
        port=account.smtp_port,
        username=account.email_address,
        password=password,
    )
    smtp_result = smtp.test_connection()
    await db.commit()
    return {"imap": imap_result, "smtp": smtp_result}


@router.post("/accounts/{account_id}/sync")
async def sync(
    account_id: str,
    payload: SyncRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> dict:
    account = await db.get(EmailAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    req = payload or SyncRequest()
    try:
        result = await sync_account(db, account, folder=req.folder, limit=req.limit)
        await db.commit()
        return result
    except Exception as exc:
        account.connected = False
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc


@router.get("/messages", response_model=Paginated[EmailMessageOut])
async def list_messages(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    classification: str | None = None,
    thread_identifier: str | None = None,
) -> Paginated[EmailMessageOut]:
    stmt = select(EmailMessage).where(EmailMessage.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(EmailMessage).where(
        EmailMessage.deleted_at.is_(None)
    )
    if classification:
        stmt = stmt.where(EmailMessage.classification == classification)
        count_stmt = count_stmt.where(EmailMessage.classification == classification)
    if thread_identifier:
        stmt = stmt.where(EmailMessage.thread_identifier == thread_identifier)
        count_stmt = count_stmt.where(EmailMessage.thread_identifier == thread_identifier)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    result = await db.execute(
        stmt.order_by(EmailMessage.received_at.desc().nullslast()).offset(offset).limit(limit)
    )
    return Paginated(items=list(result.scalars().all()), total=total, limit=limit, offset=offset)


@router.get("/threads/{thread_id}", response_model=list[EmailMessageOut])
async def get_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[EmailMessage]:
    result = await db.execute(
        select(EmailMessage)
        .where(
            EmailMessage.thread_identifier == thread_id,
            EmailMessage.deleted_at.is_(None),
        )
        .order_by(EmailMessage.received_at.asc().nullslast())
    )
    return list(result.scalars().all())
