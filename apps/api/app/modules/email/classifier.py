"""Rule-based recruitment email classifier (LLM optional later)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasons: list[str]


_PATTERNS: list[tuple[str, list[re.Pattern[str]], float]] = [
    (
        "INTERVIEW_INVITE",
        [
            re.compile(r"\b(interview|pohovor|pohovoru|zoom call|teams meeting)\b", re.I),
            re.compile(r"\b(navrhujeme termín|would like to invite|pozvánka na)\b", re.I),
        ],
        0.85,
    ),
    (
        "REJECTION",
        [
            re.compile(r"\b(unfortunately|bohužel|we will not (be )?moving|nepostupujete)\b", re.I),
            re.compile(r"\b(other candidates|jiným kandidátům|not selected|nezvolili)\b", re.I),
        ],
        0.8,
    ),
    (
        "OFFER",
        [
            re.compile(r"\b(job offer|nabídka spolupráce|offer letter|pracovní nabídk)\b", re.I),
        ],
        0.85,
    ),
    (
        "TECHNICAL_ASSIGNMENT",
        [
            re.compile(r"\b(home ?work|take[- ]home|technick\w+ úkol|coding challenge|case study)\b", re.I),
        ],
        0.8,
    ),
    (
        "APPLICATION_RECEIVED",
        [
            re.compile(r"\b(we received your application|přijali jsme vaši přihlášku|děkujeme za zájem)\b", re.I),
            re.compile(r"\b(application confirmation|potvrzení přihlášky)\b", re.I),
        ],
        0.75,
    ),
    (
        "RECRUITER_FOLLOWUP",
        [
            re.compile(r"\b(following up|navazuji|checking in|ohledně vaší kandidatury)\b", re.I),
        ],
        0.65,
    ),
    (
        "JOB_ALERT",
        [
            re.compile(r"\b(job alert|nové nabídky|recommended jobs|tipy na pozice)\b", re.I),
        ],
        0.7,
    ),
]


def classify_email(
    *,
    subject: str | None,
    text_body: str | None,
    sender: str | None = None,
) -> ClassificationResult:
    blob = f"{subject or ''}\n{text_body or ''}\n{sender or ''}"
    best_label = "UNCERTAIN"
    best_conf = 0.0
    reasons: list[str] = []

    for label, patterns, base_conf in _PATTERNS:
        hits = [p.pattern for p in patterns if p.search(blob)]
        if hits:
            conf = min(0.99, base_conf + 0.05 * (len(hits) - 1))
            if conf > best_conf:
                best_label = label
                best_conf = conf
                reasons = hits

    # Light recruiter-domain heuristic
    if best_label == "UNCERTAIN" and sender:
        if re.search(r"(careers|jobs|recruit|talent|hr@)", sender, re.I):
            return ClassificationResult("RECRUITER_OTHER", 0.4, ["sender_looks_recruitment"])

    return ClassificationResult(best_label, best_conf, reasons)
