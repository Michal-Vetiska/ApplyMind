"""Allowed application status transitions."""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable


class ApplicationStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    MATCHED = "MATCHED"
    SHORTLISTED = "SHORTLISTED"
    DRAFTED = "DRAFTED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    SUBMISSION_IN_PROGRESS = "SUBMISSION_IN_PROGRESS"
    SENT_UNCONFIRMED = "SENT_UNCONFIRMED"
    SUBMITTED = "SUBMITTED"
    EMPLOYER_REPLIED = "EMPLOYER_REPLIED"
    INTERVIEW = "INTERVIEW"
    TECHNICAL_ASSIGNMENT = "TECHNICAL_ASSIGNMENT"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    FAILED = "FAILED"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"


# Terminal-ish statuses can still move to WITHDRAWN in some cases; REJECTED/OFFER are mostly terminal.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.MATCHED,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.MATCHED: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.DRAFTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.DRAFTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.DRAFTED: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.READY_FOR_REVIEW: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.DRAFTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.APPROVED: {
        ApplicationStatus.SUBMISSION_IN_PROGRESS,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SUBMISSION_IN_PROGRESS: {
        ApplicationStatus.SENT_UNCONFIRMED,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.NEEDS_MANUAL_REVIEW,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.NEEDS_MANUAL_REVIEW: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPROVED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SENT_UNCONFIRMED: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.EMPLOYER_REPLIED,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.EMPLOYER_REPLIED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.TECHNICAL_ASSIGNMENT,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.OFFER,
    },
    ApplicationStatus.EMPLOYER_REPLIED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.TECHNICAL_ASSIGNMENT,
        ApplicationStatus.REJECTED,
        ApplicationStatus.OFFER,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.TECHNICAL_ASSIGNMENT,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.TECHNICAL_ASSIGNMENT: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
    ApplicationStatus.FAILED: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.DRAFTED,
        ApplicationStatus.WITHDRAWN,
    },
}


def normalize_status(status: str | ApplicationStatus) -> ApplicationStatus:
    if isinstance(status, ApplicationStatus):
        return status
    return ApplicationStatus(str(status).upper())


def can_transition(current: str | ApplicationStatus, new: str | ApplicationStatus) -> bool:
    cur = normalize_status(current)
    nxt = normalize_status(new)
    if cur == nxt:
        return True
    return nxt in ALLOWED_TRANSITIONS.get(cur, set())


def allowed_targets(current: str | ApplicationStatus) -> list[str]:
    cur = normalize_status(current)
    return sorted(s.value for s in ALLOWED_TRANSITIONS.get(cur, set()))


def assert_transition(current: str | ApplicationStatus, new: str | ApplicationStatus) -> None:
    if not can_transition(current, new):
        cur = normalize_status(current)
        nxt = normalize_status(new)
        raise ValueError(f"Invalid transition {cur.value} -> {nxt.value}")


def transition(
    current: str | ApplicationStatus,
    new: str | ApplicationStatus,
    *,
    evidence: Iterable[str] | None = None,
) -> ApplicationStatus:
    """Validate and return the new status. Raises ValueError if not allowed.

    Note: SMTP accepted must not jump to EMPLOYER_REPLIED / INTERVIEW / OFFER.
    Callers must supply evidence for recruiter-side statuses.
    """
    cur = normalize_status(current)
    nxt = normalize_status(new)
    if cur == nxt:
        return cur
    if not can_transition(cur, nxt):
        raise ValueError(f"Illegal application transition: {cur.value} -> {nxt.value}")

    recruiter_states = {
        ApplicationStatus.EMPLOYER_REPLIED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.TECHNICAL_ASSIGNMENT,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
    }
    if nxt in recruiter_states and not evidence:
        raise ValueError(
            f"Transition to {nxt.value} requires evidence (do not infer from SMTP acceptance alone)"
        )
    return nxt
