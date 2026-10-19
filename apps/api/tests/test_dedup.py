"""Unit tests for deduplication helpers."""

from app.services.dedup import (
    content_hash,
    is_duplicate_pair,
    job_fingerprint,
    normalize_company_name,
    normalize_title,
)


def test_normalize_company_strips_legal_suffix():
    assert normalize_company_name("Acme s.r.o.") == normalize_company_name("Acme")


def test_normalize_title_case_insensitive():
    assert normalize_title("React Developer") == normalize_title("react developer")


def test_content_hash_stable():
    a = content_hash(title="Dev", company="Acme", description="Build apps", location="Praha")
    b = content_hash(title="Dev", company="Acme", description="Build apps", location="Praha")
    assert a == b
    assert len(a) == 64


def test_content_hash_changes_with_description():
    a = content_hash(title="Dev", company="Acme", description="A", location=None)
    b = content_hash(title="Dev", company="Acme", description="B", location=None)
    assert a != b


def test_fingerprint_and_duplicate():
    h = content_hash(title="FE Dev", company="Foo", description="x")
    fp1 = job_fingerprint(
        company_normalized=normalize_company_name("Foo"),
        title_normalized=normalize_title("FE Dev"),
        content_hash_value=h,
    )
    fp2 = job_fingerprint(
        company_normalized=normalize_company_name("Foo"),
        title_normalized=normalize_title("FE Dev"),
        content_hash_value=h,
    )
    assert is_duplicate_pair(h, h, left_fingerprint=fp1, right_fingerprint=fp2)
    assert not is_duplicate_pair("aaa", "bbb")
