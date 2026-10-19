"""User profile, search profiles, and resume endpoints."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.profile import Resume, SearchProfile, UserProfile
from app.schemas.common import MessageOut
from app.schemas.profile import (
    ResumeOut,
    SearchProfileCreate,
    SearchProfileOut,
    SearchProfileUpdate,
    UserProfileOut,
    UserProfileUpdate,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=UserProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> UserProfile:
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/profile", response_model=UserProfileOut)
async def update_profile(
    payload: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
) -> UserProfile:
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    await record_audit(db, "profile.updated", "user_profile", profile.id, {})
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/search-profiles", response_model=list[SearchProfileOut])
async def list_search_profiles(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[SearchProfile]:
    result = await db.execute(select(SearchProfile).order_by(SearchProfile.created_at))
    return list(result.scalars().all())


@router.post("/search-profiles", response_model=SearchProfileOut, status_code=201)
async def create_search_profile(
    payload: SearchProfileCreate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> SearchProfile:
    profile = SearchProfile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/search-profiles/{profile_id}", response_model=SearchProfileOut)
async def update_search_profile(
    profile_id: str,
    payload: SearchProfileUpdate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> SearchProfile:
    profile = await db.get(SearchProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Search profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/search-profiles/{profile_id}", response_model=MessageOut)
async def delete_search_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    profile = await db.get(SearchProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Search profile not found")
    await db.delete(profile)
    await db.commit()
    return MessageOut(message="Deleted")


@router.get("/resumes", response_model=list[ResumeOut])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[Resume]:
    result = await db.execute(
        select(Resume).where(Resume.deleted_at.is_(None)).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/resumes", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    name: str = Form(...),
    is_default: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Resume:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".md", ".txt"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    max_bytes = settings.upload_max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    file_hash = hashlib.sha256(content).hexdigest()
    dest_dir = Path(settings.data_dir) / "resumes"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_hash}{suffix}"
    dest.write_bytes(content)

    if is_default:
        result = await db.execute(select(Resume).where(Resume.is_default.is_(True)))
        for existing in result.scalars().all():
            existing.is_default = False

    resume = Resume(
        name=name,
        file_path=str(dest),
        file_hash=file_hash,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        is_default=is_default,
        enabled=True,
        target_roles=[],
    )
    db.add(resume)
    await record_audit(db, "resume.uploaded", "resume", None, {"name": name})
    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/resumes/{resume_id}", response_model=MessageOut)
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    from datetime import UTC, datetime

    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    resume.deleted_at = datetime.now(UTC)
    resume.enabled = False
    await db.commit()
    return MessageOut(message="Deleted")
