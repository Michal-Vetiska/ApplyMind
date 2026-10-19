"""Authentication endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, hash_token
from app.core.config import get_settings
from app.core.security import generate_session_token, session_expiry, verify_password
from app.db.session import get_db
from app.models.auth import SessionToken, UserAccount
from app.schemas.auth import LoginRequest, MessageOut, UserOut
from app.services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserAccount:
    settings = get_settings()
    result = await db.execute(select(UserAccount).where(UserAccount.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    raw_token = generate_session_token()
    session = SessionToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=session_expiry(),
    )
    db.add(session)
    await record_audit(db, "auth.login", "user_account", user.id, {"email": user.email})
    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_max_age_hours * 3600,
        path="/",
    )
    return user


@router.post("/logout", response_model=MessageOut)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
) -> MessageOut:
    settings = get_settings()
    result = await db.execute(
        select(SessionToken).where(
            SessionToken.user_id == user.id,
            SessionToken.revoked_at.is_(None),
        )
    )
    for session in result.scalars().all():
        session.revoked_at = datetime.now(UTC)
    await record_audit(db, "auth.logout", "user_account", user.id, {})
    await db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return MessageOut(message="Logged out")


@router.get("/me", response_model=UserOut)
async def me(user: UserAccount = Depends(get_current_user)) -> UserAccount:
    return user
