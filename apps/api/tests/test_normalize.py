"""Unit tests for job normalization pipeline."""

from app.services.normalize import (
    classify_seniority,
    detect_seniority,
    extract_technologies,
    normalize_job,
    sanitize_html,
)


def test_sanitize_html_strips_script():
    html = "<p>Hello</p><script>alert(1)</script><style>x{}</style>"
    text = sanitize_html(html)
    assert text is not None
    assert "Hello" in text
    assert "alert" not in text
    assert "x{}" not in text


def test_extract_technologies_prefers_longer():
    text = "We use React Native and React with TypeScript and PostgreSQL."
    techs = extract_technologies(text)
    assert "React Native" in techs
    assert "TypeScript" in techs
    assert "PostgreSQL" in techs


def test_detect_seniority_junior():
    assert detect_seniority("Junior React Developer", "") == "junior"
    assert classify_seniority("Junior React Developer") == "junior"


def test_normalize_job_pipeline():
    result = normalize_job(
        title="Junior React Developer",
        company_name="Example s.r.o.",
        description_html="<p>React, TypeScript, Docker. Plat 55 000 Kč.</p>",
        location="Prague",
        salary_text="55 000 Kč / měsíc",
    )
    assert result.normalized_title
    assert result.normalized_company
    assert result.location in {"Praha", "Prague"}
    assert "React" in result.technologies or "TypeScript" in result.technologies
    assert result.seniority == "junior"
    assert result.salary is not None
    assert result.salary.salary_flag in {"PARSED", "PARTIAL"}
    assert result.content_hash
