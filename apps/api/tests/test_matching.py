"""Unit tests for explainable matching engine."""

from types import SimpleNamespace

from app.modules.matching.engine import MatchingEngine, MatchWeights, score_job


def _profile(**kwargs):
    defaults = dict(
        technologies=["React", "TypeScript", "Python"],
        seniority=["junior", "junior_medior", "medior"],
        locations=["Praha"],
        remote_preferences=["hybrid_prague", "remote_cz"],
        minimum_salary=40000,
        preferred_salary_min=50000,
        preferred_salary_max=70000,
        salary_currency="CZK",
        employment_types=["full_time"],
        job_titles={"high": ["React Developer"], "medium": [], "optional": []},
        exclusion_rules=[
            "senior_management_unrelated",
            "mandatory_certifications_not_held",
            "incompatible_specialist",
        ],
        matching_threshold=60.0,
        weight_technology=0.35,
        weight_seniority=0.20,
        weight_location=0.20,
        weight_compensation=0.15,
        weight_other=0.10,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _job(**kwargs):
    defaults = dict(
        title="React Developer",
        technologies=["React", "TypeScript"],
        seniority="junior",
        location="Praha",
        remote_type="hybrid",
        employment_type="full_time",
        salary_min=55000,
        salary_max=65000,
        currency="CZK",
        salary_flag="PARSED",
        description="Frontend role",
        normalized_description="Frontend role",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_good_match_shortlists():
    result = score_job(_profile(), _job())
    assert result.overall_score >= 60
    assert result.decision == "SHORTLIST"
    assert not result.excluded


def test_salary_unknown_not_hard_reject():
    result = score_job(
        _profile(),
        _job(salary_min=None, salary_max=None, salary_flag="SALARY_UNKNOWN", currency=None),
    )
    assert result.compensation_score == 50.0
    assert result.decision != "EXCLUDE"
    assert result.explanation["components"]["compensation"]["salary_flag"] == "SALARY_UNKNOWN"


def test_hard_exclusion_senior_management():
    result = score_job(
        _profile(),
        _job(title="Head of Sales", description="Lead sales organization", seniority="lead"),
    )
    assert result.excluded
    assert result.decision == "EXCLUDE"
    assert result.overall_score == 0.0


def test_custom_weights():
    engine = MatchingEngine(weights=MatchWeights(technology=1.0, seniority=0, location=0, compensation=0, other=0))
    result = engine.evaluate(_profile(), _job(technologies=["React", "TypeScript", "Python"]))
    assert result.skill_score == 100.0
    assert abs(result.overall_score - 100.0) < 0.01
