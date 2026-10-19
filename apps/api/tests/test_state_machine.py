"""Unit tests for application status transitions."""

import pytest

from app.modules.applications.state_machine import (
    ApplicationStatus,
    allowed_targets,
    can_transition,
    transition,
)


def test_drafted_to_ready_to_approved():
    assert can_transition("DRAFTED", "READY_FOR_REVIEW")
    assert can_transition("READY_FOR_REVIEW", "APPROVED")
    assert transition("DRAFTED", "READY_FOR_REVIEW") == ApplicationStatus.READY_FOR_REVIEW
    assert transition("READY_FOR_REVIEW", "APPROVED") == ApplicationStatus.APPROVED


def test_illegal_jump_raises():
    with pytest.raises(ValueError):
        transition("DRAFTED", "OFFER")


def test_recruiter_state_requires_evidence():
    with pytest.raises(ValueError, match="evidence"):
        transition("SUBMITTED", "INTERVIEW")
    assert (
        transition("SUBMITTED", "INTERVIEW", evidence=["recruiter email classified INTERVIEW_INVITE"])
        == ApplicationStatus.INTERVIEW
    )


def test_smtp_cannot_imply_offer():
    assert not can_transition("SUBMISSION_IN_PROGRESS", "OFFER")
    assert can_transition("SUBMISSION_IN_PROGRESS", "SENT_UNCONFIRMED")


def test_allowed_targets_lists():
    targets = allowed_targets(ApplicationStatus.APPROVED)
    assert "SUBMISSION_IN_PROGRESS" in targets
    assert "OFFER" not in targets
