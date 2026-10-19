"""Explainable matching engine with configurable weights and hard exclusions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatchWeights:
    technology: float = 0.35
    seniority: float = 0.20
    location: float = 0.20
    compensation: float = 0.15
    other: float = 0.10

    def normalized(self) -> MatchWeights:
        total = self.technology + self.seniority + self.location + self.compensation + self.other
        if total <= 0:
            return MatchWeights()
        return MatchWeights(
            technology=self.technology / total,
            seniority=self.seniority / total,
            location=self.location / total,
            compensation=self.compensation / total,
            other=self.other / total,
        )


@dataclass
class MatchResult:
    overall_score: float
    skill_score: float
    seniority_score: float
    location_score: float
    compensation_score: float
    other_score: float
    decision: str
    explanation: dict[str, Any] = field(default_factory=dict)
    missing_skills: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    excluded: bool = False
    exclusion_reasons: list[str] = field(default_factory=list)


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _tech_set(items: list | None) -> set[str]:
    return {_norm(str(t)) for t in (items or []) if str(t).strip()}


def score_skills(profile_tech: list, job_tech: list) -> tuple[float, list[str], dict]:
    """Score coverage of job-required technologies by the candidate profile."""
    profile = _tech_set(profile_tech)
    required = _tech_set(job_tech)
    if not required:
        # Job listing without tech tags — partial credit, do not hard-fail
        return 50.0, [], {
            "note": "Job has no extracted technologies",
            "matched": [],
            "missing": [],
        }
    if not profile:
        return 20.0, sorted(required), {
            "note": "No profile technologies configured",
            "matched": [],
            "missing": sorted(required),
        }
    matched = sorted(required & profile)
    missing = sorted(required - profile)
    ratio = len(matched) / len(required)
    score = round(ratio * 100, 2)
    return score, missing, {
        "matched": matched,
        "missing": missing,
        "job_technologies": sorted(required),
    }


def score_seniority(profile_levels: list, job_seniority: str | None) -> tuple[float, dict]:
    levels = {_norm(x) for x in (profile_levels or [])}
    job = _norm(job_seniority)
    if not levels:
        return 50.0, {"note": "No seniority preference", "job": job or None}
    if not job:
        return 55.0, {"note": "Job seniority unknown", "accepted": sorted(levels)}
    # Exact / synonym map
    synonyms = {
        "jr": "junior",
        "junior/medior": "junior_medior",
        "mid": "medior",
        "middle": "medior",
        "mid-level": "medior",
        "sr": "senior",
    }
    job = synonyms.get(job, job)
    if job in levels:
        return 100.0, {"match": "exact", "job": job}
    # Adjacent compatibility
    adjacency = {
        "intern": {"junior"},
        "junior": {"intern", "junior_medior", "practical_equivalent"},
        "junior_medior": {"junior", "medior", "practical_equivalent"},
        "medior": {"junior_medior", "practical_equivalent"},
        "practical_equivalent": {"junior", "junior_medior", "medior"},
        "senior": set(),
        "lead": set(),
    }
    if job in {"senior", "lead"} and job not in levels:
        return 10.0, {"match": "too_senior", "job": job, "accepted": sorted(levels)}
    neighbors = adjacency.get(job, set())
    if neighbors & levels:
        return 70.0, {"match": "adjacent", "job": job}
    return 25.0, {"match": "mismatch", "job": job, "accepted": sorted(levels)}


def score_location(
    profile_locations: list,
    remote_prefs: list,
    job_location: str | None,
    job_remote: str | None,
) -> tuple[float, dict]:
    prefs_loc = [_norm(x) for x in (profile_locations or [])]
    prefs_remote = {_norm(x) for x in (remote_prefs or [])}
    loc = _norm(job_location)
    remote = _norm(job_remote)

    evidence: dict[str, Any] = {"job_location": job_location, "job_remote": job_remote}

    if remote:
        remote_aliases = {
            "remote": {"remote", "remote_cz", "fully_remote"},
            "remote_cz": {"remote", "remote_cz"},
            "hybrid": {"hybrid", "hybrid_prague"},
            "onsite": {"onsite", "onsite_prague"},
            "hybrid_prague": {"hybrid", "hybrid_prague"},
            "onsite_prague": {"onsite", "onsite_prague"},
        }
        for pref in prefs_remote:
            aliases = remote_aliases.get(pref, {pref})
            if remote in aliases or any(a in remote for a in aliases):
                evidence["match"] = "remote_preference"
                return 100.0, evidence

    if loc and prefs_loc:
        for pref in prefs_loc:
            if pref and (pref in loc or loc in pref):
                evidence["match"] = "location_substring"
                return 95.0, evidence
            # Praha / Prague
            if "praha" in pref and ("praha" in loc or "prague" in loc):
                evidence["match"] = "prague_alias"
                return 95.0, evidence

    if not loc and not remote:
        evidence["match"] = "unknown_location"
        return 50.0, evidence

    evidence["match"] = "weak"
    return 30.0, evidence


def score_compensation(
    *,
    minimum_salary: int | None,
    preferred_min: int | None,
    preferred_max: int | None,
    currency: str | None,
    job_min: int | None,
    job_max: int | None,
    job_currency: str | None,
    salary_flag: str | None,
) -> tuple[float, dict]:
    flag = salary_flag or "SALARY_UNKNOWN"
    evidence: dict[str, Any] = {
        "salary_flag": flag,
        "job_min": job_min,
        "job_max": job_max,
        "job_currency": job_currency,
        "profile_minimum": minimum_salary,
        "preferred_range": [preferred_min, preferred_max],
    }

    if flag == "SALARY_UNKNOWN" or (job_min is None and job_max is None):
        evidence["note"] = "Compensation unknown — not penalized as rejection"
        return 50.0, evidence

    # Currency mismatch → cautious score, do not invent FX conversion
    if currency and job_currency and _norm(currency) != _norm(job_currency):
        evidence["note"] = "Currency mismatch — no FX conversion applied"
        return 45.0, evidence

    job_low = job_min if job_min is not None else job_max
    job_high = job_max if job_max is not None else job_min
    assert job_low is not None and job_high is not None

    if minimum_salary is not None and job_high < minimum_salary:
        evidence["note"] = "Below minimum salary"
        return 15.0, evidence

    if preferred_min is not None and preferred_max is not None:
        # Overlap ratio with preferred band
        overlap_start = max(job_low, preferred_min)
        overlap_end = min(job_high, preferred_max)
        if overlap_end >= overlap_start:
            evidence["note"] = "Overlaps preferred range"
            return 100.0, evidence
        if job_low > preferred_max:
            evidence["note"] = "Above preferred max"
            return 85.0, evidence
        distance = preferred_min - job_high
        if distance <= preferred_min * 0.15:
            evidence["note"] = "Slightly below preferred min"
            return 70.0, evidence
        evidence["note"] = "Outside preferred range"
        return 40.0, evidence

    if minimum_salary is not None and job_low >= minimum_salary:
        evidence["note"] = "Meets minimum"
        return 80.0, evidence

    evidence["note"] = "Partial compensation data"
    return 60.0, evidence


def score_other(
    *,
    profile_titles: dict | None,
    job_title: str | None,
    employment_types: list | None,
    job_employment: str | None,
) -> tuple[float, dict]:
    title = _norm(job_title)
    evidence: dict[str, Any] = {"job_title": job_title}
    score = 50.0

    titles = profile_titles or {}
    high = [_norm(t) for t in titles.get("high", [])]
    medium = [_norm(t) for t in titles.get("medium", [])]
    optional = [_norm(t) for t in titles.get("optional", [])]

    def title_hit(candidates: list[str]) -> bool:
        return any(c and (c in title or title in c) for c in candidates)

    if title_hit(high):
        score = 100.0
        evidence["title_band"] = "high"
    elif title_hit(medium):
        score = 75.0
        evidence["title_band"] = "medium"
    elif title_hit(optional):
        score = 60.0
        evidence["title_band"] = "optional"
    else:
        evidence["title_band"] = "none"

    prefs_emp = {_norm(x) for x in (employment_types or [])}
    if prefs_emp and job_employment:
        if _norm(job_employment) in prefs_emp:
            score = min(100.0, score + 10)
            evidence["employment"] = "match"
        else:
            score = max(0.0, score - 15)
            evidence["employment"] = "mismatch"

    return round(score, 2), evidence


def check_hard_exclusions(
    exclusion_rules: list | None,
    *,
    job_title: str | None,
    job_seniority: str | None,
    job_description: str | None,
) -> list[str]:
    reasons: list[str] = []
    rules = set(exclusion_rules or [])
    blob = f"{job_title or ''}\n{job_description or ''}".lower()
    sen = _norm(job_seniority)

    if "senior_management_unrelated" in rules:
        if any(
            k in blob
            for k in (
                "head of sales",
                "sales director",
                "marketing director",
                "hr director",
                "chief financial",
                "chief marketing",
                "chief executive",
                "cfo",
                "cmo",
                "ceo ",
                "vp of",
                "vice president",
            )
        ) or (
            sen in {"lead", "senior"}
            and any(k in blob for k in ("sales", "marketing", "hr ", "finance"))
            and "developer" not in blob
            and "engineer" not in blob
        ):
            reasons.append("senior_management_unrelated")

    if "mandatory_certifications_not_held" in rules:
        if any(
            k in blob
            for k in (
                "mandatory cisco",
                "povinná certifikace",
                "cissp required",
                "aws certified solutions architect required",
                "must hold certification",
            )
        ):
            reasons.append("mandatory_certifications_not_held")

    if "incompatible_specialist" in rules:
        specialist_keywords = (
            "embedded c++ only",
            "asic design",
            "fpga",
            "sap consultant",
            "mainframe",
            "cobol",
            "oracle ebs",
        )
        if any(k in blob for k in specialist_keywords):
            reasons.append("incompatible_specialist")

    return reasons


class MatchingEngine:
    def __init__(self, weights: MatchWeights | None = None, threshold: float = 60.0):
        self.weights = (weights or MatchWeights()).normalized()
        self.threshold = threshold

    @classmethod
    def from_search_profile(cls, profile: Any) -> MatchingEngine:
        weights = MatchWeights(
            technology=float(getattr(profile, "weight_technology", 0.35)),
            seniority=float(getattr(profile, "weight_seniority", 0.20)),
            location=float(getattr(profile, "weight_location", 0.20)),
            compensation=float(getattr(profile, "weight_compensation", 0.15)),
            other=float(getattr(profile, "weight_other", 0.10)),
        )
        threshold = float(getattr(profile, "matching_threshold", 60.0))
        return cls(weights=weights, threshold=threshold)

    def evaluate(self, profile: Any, job: Any) -> MatchResult:
        exclusions = check_hard_exclusions(
            getattr(profile, "exclusion_rules", None),
            job_title=getattr(job, "title", None),
            job_seniority=getattr(job, "seniority", None),
            job_description=getattr(job, "normalized_description", None)
            or getattr(job, "description", None),
        )
        if exclusions:
            return MatchResult(
                overall_score=0.0,
                skill_score=0.0,
                seniority_score=0.0,
                location_score=0.0,
                compensation_score=0.0,
                other_score=0.0,
                decision="EXCLUDE",
                explanation={"hard_exclusions": exclusions},
                missing_skills=[],
                evidence={"exclusions": exclusions},
                excluded=True,
                exclusion_reasons=exclusions,
            )

        skill_score, missing, skill_ev = score_skills(
            getattr(profile, "technologies", None),
            getattr(job, "technologies", None) or [],
        )
        sen_score, sen_ev = score_seniority(
            getattr(profile, "seniority", None),
            getattr(job, "seniority", None),
        )
        loc_score, loc_ev = score_location(
            getattr(profile, "locations", None),
            getattr(profile, "remote_preferences", None),
            getattr(job, "location", None),
            getattr(job, "remote_type", None),
        )
        comp_score, comp_ev = score_compensation(
            minimum_salary=getattr(profile, "minimum_salary", None),
            preferred_min=getattr(profile, "preferred_salary_min", None),
            preferred_max=getattr(profile, "preferred_salary_max", None),
            currency=getattr(profile, "salary_currency", None),
            job_min=getattr(job, "salary_min", None),
            job_max=getattr(job, "salary_max", None),
            job_currency=getattr(job, "currency", None),
            salary_flag=getattr(job, "salary_flag", None),
        )
        other_score, other_ev = score_other(
            profile_titles=getattr(profile, "job_titles", None),
            job_title=getattr(job, "title", None),
            employment_types=getattr(profile, "employment_types", None),
            job_employment=getattr(job, "employment_type", None),
        )

        w = self.weights
        overall = round(
            skill_score * w.technology
            + sen_score * w.seniority
            + loc_score * w.location
            + comp_score * w.compensation
            + other_score * w.other,
            2,
        )

        if overall >= self.threshold:
            decision = "SHORTLIST"
        elif overall >= max(40.0, self.threshold - 20):
            decision = "REVIEW"
        else:
            decision = "REJECT"

        return MatchResult(
            overall_score=overall,
            skill_score=skill_score,
            seniority_score=sen_score,
            location_score=loc_score,
            compensation_score=comp_score,
            other_score=other_score,
            decision=decision,
            explanation={
                "weights": {
                    "technology": w.technology,
                    "seniority": w.seniority,
                    "location": w.location,
                    "compensation": w.compensation,
                    "other": w.other,
                },
                "threshold": self.threshold,
                "components": {
                    "skill": skill_ev,
                    "seniority": sen_ev,
                    "location": loc_ev,
                    "compensation": comp_ev,
                    "other": other_ev,
                },
            },
            missing_skills=missing,
            evidence={
                "skill": skill_ev,
                "seniority": sen_ev,
                "location": loc_ev,
                "compensation": comp_ev,
                "other": other_ev,
            },
        )


def score_job(profile: Any, job: Any) -> MatchResult:
    """Module-level convenience wrapper."""
    return MatchingEngine.from_search_profile(profile).evaluate(profile, job)


def evaluate_match(
    *,
    job_title: str,
    job_technologies: list,
    job_seniority: str | None,
    job_location: str | None,
    remote_type: str | None,
    salary_min: int | None,
    salary_max: int | None,
    salary_flag: str,
    salary_period: str | None,
    profile_technologies: list,
    profile_seniority: list,
    profile_locations: list,
    remote_preferences: list,
    minimum_salary: int | None,
    preferred_salary_min: int | None,
    preferred_salary_max: int | None,
    exclusion_rules: list,
    job_titles_priority: dict,
    matching_threshold: float = 60.0,
    weight_technology: float = 0.35,
    weight_seniority: float = 0.20,
    weight_location: float = 0.20,
    weight_compensation: float = 0.15,
    weight_other: float = 0.10,
) -> MatchResult:
    """Compatibility wrapper used by API routes and tests."""

    class _P:
        pass

    profile = _P()
    profile.technologies = profile_technologies
    profile.seniority = profile_seniority
    profile.locations = profile_locations
    profile.remote_preferences = remote_preferences
    profile.minimum_salary = minimum_salary
    profile.preferred_salary_min = preferred_salary_min
    profile.preferred_salary_max = preferred_salary_max
    profile.salary_currency = "CZK"
    profile.exclusion_rules = exclusion_rules
    profile.job_titles = job_titles_priority
    profile.employment_types = []
    profile.matching_threshold = matching_threshold
    profile.weight_technology = weight_technology
    profile.weight_seniority = weight_seniority
    profile.weight_location = weight_location
    profile.weight_compensation = weight_compensation
    profile.weight_other = weight_other

    job = _P()
    job.title = job_title
    job.technologies = job_technologies
    job.seniority = job_seniority
    job.location = job_location
    job.remote_type = remote_type
    job.salary_min = salary_min
    job.salary_max = salary_max
    job.salary_flag = salary_flag
    job.currency = "CZK"
    job.employment_type = None
    job.description = None
    job.normalized_description = None

    result = score_job(profile, job)
    decision_map = {
        "SHORTLIST": "RECOMMENDED",
        "EXCLUDE": "REJECTED",
        "REJECT": "LOW_PRIORITY",
        "REVIEW": "REVIEW",
    }
    result.decision = decision_map.get(result.decision, result.decision)
    components = (result.explanation or {}).get("components", {})
    skill_ev = components.get("skill") or {}
    result.matched_skills = list(skill_ev.get("matched") or skill_ev.get("matched_skills") or [])  # type: ignore[attr-defined]
    result.reasons = []  # type: ignore[attr-defined]
    for key, ev in components.items():
        if isinstance(ev, dict) and ev.get("note"):
            result.reasons.append(str(ev["note"]))  # type: ignore[attr-defined]
    comp = components.get("compensation") or {}
    uncertainties: list[str] = []
    if isinstance(comp, dict) and comp.get("note"):
        uncertainties.append(str(comp["note"]))
    if salary_flag == "SALARY_UNKNOWN" or (salary_min is None and salary_max is None):
        uncertainties.append("Compensation not specified — not treated as mismatch")
    result.uncertainties = uncertainties  # type: ignore[attr-defined]
    result.hard_reject = bool(result.excluded)  # type: ignore[attr-defined]
    return result
