"""Czech / EU salary text parser.

Never invents compensation values. Missing or ambiguous text yields SALARY_UNKNOWN.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SalaryFlag = Literal["PARSED", "SALARY_UNKNOWN", "PARTIAL"]
SalaryPeriod = Literal["month", "year", "hour", "day", "unknown"]

# Number formats: 50 000, 50.000, 50,000, 50k, 50tis (prefer k/tis before bare digits)
_NUM = (
    r"(?:\d{1,3}(?:[.,\s]\d{3})+"
    r"|\d+\s*[kK]"
    r"|\d+(?:\s*(?:tis\.?|tisíc))"
    r"|\d+(?:[.,]\d+)?)"
)
_CURRENCY_TOKEN = r"(?:kč|kc|czk|eur|€|usd|\$|gbp|£|pln)?"

_CURRENCY_MAP = {
    "kč": "CZK",
    "kc": "CZK",
    "czk": "CZK",
    "eur": "EUR",
    "€": "EUR",
    "usd": "USD",
    "$": "USD",
    "gbp": "GBP",
    "£": "GBP",
    "pln": "PLN",
}

_PERIOD_PATTERNS: list[tuple[re.Pattern[str], SalaryPeriod]] = [
    (re.compile(r"(?:/\s*měs(?:íc)?|per\s*month|monthly|měsíčně|měs\.?)", re.I), "month"),
    (re.compile(r"(?:/\s*rok|per\s*year|yearly|annually|ročně|p\.?\s*a\.?)", re.I), "year"),
    (re.compile(r"(?:/\s*hod(?:ina)?|per\s*hour|hourly|hodinově)", re.I), "hour"),
    (re.compile(r"(?:/\s*den|per\s*day|daily|denně)", re.I), "day"),
]


@dataclass(frozen=True)
class ParsedSalary:
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    salary_period: SalaryPeriod
    original_salary_text: str | None
    salary_flag: SalaryFlag

    def as_dict(self) -> dict:
        return {
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "currency": self.currency,
            "salary_period": self.salary_period if self.salary_period != "unknown" else None,
            "original_salary_text": self.original_salary_text,
            "salary_flag": self.salary_flag,
        }


def _unknown(original: str | None = None) -> ParsedSalary:
    return ParsedSalary(
        salary_min=None,
        salary_max=None,
        currency=None,
        salary_period="unknown",
        original_salary_text=original.strip() if original and original.strip() else None,
        salary_flag="SALARY_UNKNOWN",
    )


def _parse_number(raw: str) -> int | None:
    s = raw.strip().lower().replace("\xa0", " ")
    if not s:
        return None

    multiplier = 1
    if re.search(r"\btis\.?\b|\btisíc\b", s):
        multiplier = 1000
        s = re.sub(r"\s*(tis\.?|tisíc)\s*", "", s)
    if s.endswith("k") and not s.endswith("kč"):
        multiplier = 1000
        s = s[:-1]

    s = s.replace(" ", "")
    # Thousands separators: 50.000 / 50,000 / 50 000 (spaces already removed)
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    else:
        # Decimal comma only when not a thousands grouping
        s = s.replace(",", ".")

    try:
        value = float(s)
    except ValueError:
        return None

    result = int(round(value * multiplier))
    return result if result > 0 else None


def _detect_currency(text: str) -> str | None:
    lower = text.lower()
    # Prefer explicit currency tokens
    for token, code in sorted(_CURRENCY_MAP.items(), key=lambda x: -len(x[0])):
        if token in {"$", "€", "£"}:
            if token in text:
                return code
        else:
            pattern = rf"(?<![a-z]){re.escape(token)}(?![a-z])"
            if re.search(pattern, lower):
                return code
    return None


def _detect_period(text: str) -> SalaryPeriod:
    for pattern, period in _PERIOD_PATTERNS:
        if pattern.search(text):
            return period
    # Default for CZK without period is monthly (common CZ convention) only when currency is CZK
    # — but we must not invent; leave unknown unless explicit or strongly conventional phrasing.
    if re.search(r"\bhrub(?:ého|ý|á)\b", text, re.I):
        return "month"
    return "unknown"


def parse_salary(text: str | None) -> ParsedSalary:
    """Alias used by normalization pipeline and tests."""
    return parse_salary_text(text)


def parse_salary_text(text: str | None) -> ParsedSalary:
    """Parse free-text salary. Returns SALARY_UNKNOWN when nothing reliable can be extracted."""
    if text is None:
        return _unknown(None)
    original = text.strip()
    if not original:
        return _unknown(None)

    # Explicit unknowns
    if re.search(
        r"(?:neuvedeno|nesděleno|dle dohody|by agreement|competitive|negotiable|"
        r"odměna individuální|salary not (?:listed|specified))",
        original,
        re.I,
    ) and not re.search(_NUM, original):
        return _unknown(original)

    currency = _detect_currency(original)
    period = _detect_period(original)

    # Range patterns: 50-70k, 50 000 – 70 000, od 50 000 do 70 000, €45,000 - €55,000
    range_patterns = [
        rf"(?P<min>{_NUM})\s*{_CURRENCY_TOKEN}\s*(?:-|–|—|až|to|~)\s*{_CURRENCY_TOKEN}\s*(?P<max>{_NUM})",
        rf"(?:od|from)\s*(?P<min>{_NUM})\s*(?:do|to|až|-|–)\s*(?P<max>{_NUM})",
    ]
    for pat in range_patterns:
        m = re.search(pat, original, re.I)
        if m:
            raw_min = m.group("min")
            raw_max = m.group("max")
            # "60-80k" → apply k/tis multiplier to both sides when only max has it
            if re.search(r"[kK]\s*$", raw_max) and not re.search(r"[kK]|tis", raw_min, re.I):
                raw_min = raw_min + "k"
            if re.search(r"tis", raw_max, re.I) and not re.search(r"tis|[kK]", raw_min, re.I):
                raw_min = raw_min + " tis"
            lo = _parse_number(raw_min)
            hi = _parse_number(raw_max)
            if lo is None and hi is None:
                continue
            if lo is not None and hi is not None and lo > hi:
                lo, hi = hi, lo
            flag: SalaryFlag = "PARSED" if lo is not None and hi is not None else "PARTIAL"
            if currency is None and period == "unknown" and lo is None and hi is None:
                return _unknown(original)
            # If we only have numbers with no currency in CZ context, still keep numbers but flag PARTIAL
            if currency is None:
                flag = "PARTIAL"
            return ParsedSalary(
                salary_min=lo,
                salary_max=hi,
                currency=currency,
                salary_period=period if period != "unknown" else ("month" if currency == "CZK" else period),
                original_salary_text=original,
                salary_flag=flag,
            )

    # Single value: od 60 000 / 60 000 Kč / up to 80k
    single_patterns = [
        rf"(?:od|from|min\.?)\s*(?P<min>{_NUM})",
        rf"(?:do|up to|max\.?|až)\s*(?P<max>{_NUM})",
        rf"(?P<val>{_NUM})\s*(?:kč|kc|czk|eur|€|usd|\$|gbp|£|pln)?",
    ]
    for pat in single_patterns:
        m = re.search(pat, original, re.I)
        if not m:
            continue
        groups = m.groupdict()
        lo = _parse_number(groups["min"]) if "min" in groups and groups.get("min") else None
        hi = _parse_number(groups["max"]) if "max" in groups and groups.get("max") else None
        val = _parse_number(groups["val"]) if "val" in groups and groups.get("val") else None
        if val is not None:
            lo = hi = val
        if lo is None and hi is None:
            continue
        resolved_period = period
        if resolved_period == "unknown" and currency == "CZK":
            resolved_period = "month"
        return ParsedSalary(
            salary_min=lo,
            salary_max=hi,
            currency=currency,
            salary_period=resolved_period,
            original_salary_text=original,
            salary_flag="PARTIAL" if currency is None or (lo is None) != (hi is None) else "PARSED",
        )

    return _unknown(original)


def apply_salary_to_job_fields(text: str | None) -> dict:
    """Convenience helper returning fields matching the Job model columns."""
    return parse_salary_text(text).as_dict()
