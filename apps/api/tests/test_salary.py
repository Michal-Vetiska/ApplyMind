"""Unit tests for CZ/EU salary parser."""

from app.services.salary import parse_salary_text


def test_parse_czk_range():
    result = parse_salary_text("50 000 – 70 000 Kč / měsíc")
    assert result.salary_flag == "PARSED"
    assert result.salary_min == 50000
    assert result.salary_max == 70000
    assert result.currency == "CZK"
    assert result.salary_period == "month"


def test_parse_od_do():
    result = parse_salary_text("od 60 tis. do 80 tis. Kč")
    assert result.salary_min == 60000
    assert result.salary_max == 80000
    assert result.currency == "CZK"


def test_parse_eur_yearly():
    result = parse_salary_text("€45,000 - €55,000 per year")
    assert result.salary_min == 45000
    assert result.salary_max == 55000
    assert result.currency == "EUR"
    assert result.salary_period == "year"


def test_salary_unknown_when_missing():
    result = parse_salary_text(None)
    assert result.salary_flag == "SALARY_UNKNOWN"
    assert result.salary_min is None
    assert result.salary_max is None


def test_salary_unknown_when_negotiable_without_numbers():
    result = parse_salary_text("dle dohody")
    assert result.salary_flag == "SALARY_UNKNOWN"
    assert result.original_salary_text == "dle dohody"


def test_never_invents_from_empty():
    result = parse_salary_text("   ")
    assert result.salary_flag == "SALARY_UNKNOWN"
    assert result.salary_min is None


def test_k_suffix():
    result = parse_salary_text("60-80k CZK monthly")
    assert result.salary_min == 60000
    assert result.salary_max == 80000
    assert result.currency == "CZK"
