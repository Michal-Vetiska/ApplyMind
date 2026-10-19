"""Job normalization pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from app.services.dedup import content_hash, normalize_company_name, normalize_title
from app.services.salary import ParsedSalary, parse_salary

KNOWN_TECH = [
    "react native",
    "react",
    "vue.js",
    "vue",
    "typescript",
    "javascript",
    "laravel",
    "php",
    "postgresql",
    "postgres",
    "supabase",
    "docker",
    "kubernetes",
    "python",
    "fastapi",
    "node.js",
    "nodejs",
    "expo",
    "next.js",
    "nextjs",
    "tailwind",
    "graphql",
    "redis",
    "aws",
    "azure",
    "ci/cd",
    "github actions",
]


@dataclass
class NormalizedJob:
    title: str
    normalized_title: str
    company_name: str | None
    normalized_company: str | None
    description_text: str | None
    location: str | None
    remote_type: str | None
    employment_type: str | None
    seniority: str | None
    technologies: list[str] = field(default_factory=list)
    salary: ParsedSalary | None = None
    content_hash: str | None = None
    requirements: dict = field(default_factory=dict)

    # Back-compat aliases
    @property
    def description(self) -> str | None:
        return self.description_text

    @property
    def normalized_description(self) -> str | None:
        return self.description_text.lower() if self.description_text else None

    @property
    def requirements_json(self) -> dict:
        return self.requirements

    @property
    def salary_min(self) -> int | None:
        return self.salary.salary_min if self.salary else None

    @property
    def salary_max(self) -> int | None:
        return self.salary.salary_max if self.salary else None

    @property
    def currency(self) -> str | None:
        return self.salary.currency if self.salary else None

    @property
    def salary_period(self) -> str | None:
        if not self.salary:
            return None
        period = self.salary.salary_period
        return None if period == "unknown" else period

    @property
    def original_salary_text(self) -> str | None:
        return self.salary.original_salary_text if self.salary else None

    @property
    def salary_flag(self) -> str:
        return self.salary.salary_flag if self.salary else "SALARY_UNKNOWN"


def sanitize_html(html: str | None) -> str | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "iframe", "object", "embed"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_technologies(text: str | None) -> list[str]:
    if not text:
        return []
    lower = text.lower()
    found: list[str] = []
    for tech in KNOWN_TECH:
        if tech in lower:
            label = {
                "vue.js": "Vue.js",
                "react native": "React Native",
                "react": "React",
                "typescript": "TypeScript",
                "javascript": "JavaScript",
                "node.js": "Node.js",
                "nodejs": "Node.js",
                "next.js": "Next.js",
                "nextjs": "Next.js",
                "postgres": "PostgreSQL",
                "postgresql": "PostgreSQL",
                "ci/cd": "CI/CD",
                "github actions": "GitHub Actions",
                "php": "PHP",
                "aws": "AWS",
            }.get(tech, tech.title() if tech.islower() else tech)
            if label not in found:
                found.append(label)
    return found


def detect_seniority(title: str, description: str = "") -> str | None:
    """Alias for classify_seniority."""
    return classify_seniority(title, description)


def detect_seniority(title: str, description: str | None = None) -> str | None:
    return classify_seniority(title, description)


def classify_seniority(title: str, description: str | None = None) -> str | None:
    blob = f"{title} {description or ''}".lower()
    if re.search(r"\b(senior|sr\.?)\b", blob) and not re.search(r"\b(junior|medior|mid)\b", blob):
        return "senior"
    if re.search(r"\b(junior|jr\.?)\b", blob) and re.search(r"\b(medior|mid|middle)\b", blob):
        return "junior_medior"
    if re.search(r"\b(junior|jr\.?)\b", blob):
        return "junior"
    if re.search(r"\b(medior|mid-level|mid level|middle)\b", blob):
        return "medior"
    return None


def classify_remote(location: str | None, description: str | None = None) -> str | None:
    blob = f"{location or ''} {description or ''}".lower()
    if re.search(r"fully remote|100%\s*remote|plně remote|plne remote|remote only", blob):
        return "remote"
    if "hybrid" in blob or "hybridní" in blob:
        return "hybrid"
    if "remote" in blob:
        return "remote"
    if location:
        return "onsite"
    return None


def classify_employment(text: str | None) -> str | None:
    if not text:
        return None
    lower = text.lower()
    mapping = [
        ("full-time", "full_time"),
        ("full time", "full_time"),
        ("plný úvazek", "full_time"),
        ("part-time", "part_time"),
        ("částečný", "part_time"),
        ("dpč", "dpc"),
        ("dpp", "dpp"),
        ("ičo", "ico"),
        ("freelance", "contract"),
        ("contract", "contract"),
    ]
    for needle, value in mapping:
        if needle in lower:
            return value
    return None


def normalize_job(
    *,
    title: str,
    company_name: str | None = None,
    description_html: str | None = None,
    description_text: str | None = None,
    location: str | None = None,
    remote_type: str | None = None,
    employment_type: str | None = None,
    seniority: str | None = None,
    original_salary_text: str | None = None,
    salary_text: str | None = None,
    technologies_hint: list[str] | None = None,
) -> NormalizedJob:
    if description_html and "<" in description_html:
        description = sanitize_html(description_html)
    else:
        description = description_text or description_html

    salary = parse_salary(salary_text or original_salary_text)
    if salary.salary_flag == "SALARY_UNKNOWN" and description:
        snippet_match = re.search(
            r"((?:salary|mzda|odměna|odmena|compensation)[^\n.]{0,80})",
            description,
            re.IGNORECASE,
        )
        if snippet_match:
            salary = parse_salary(snippet_match.group(1))

    technologies = list(technologies_hint or [])
    for tech in extract_technologies(f"{title}\n{description or ''}"):
        if tech not in technologies:
            technologies.append(tech)

    seniority = seniority or classify_seniority(title, description)
    remote = remote_type or classify_remote(location, description)
    employment = employment_type or classify_employment(f"{title} {description or ''}")
    normalized_location = location
    if location:
        normalized_location = re.sub(r"\s+", " ", location.strip())
        normalized_location = re.sub(r"(?i)^prague\b", "Praha", normalized_location)
        normalized_location = re.sub(r"(?i)^prag\b", "Praha", normalized_location)
    hash_value = content_hash(
        title=title,
        company=company_name,
        description=description,
        location=normalized_location,
    )

    return NormalizedJob(
        title=title.strip(),
        normalized_title=normalize_title(title),
        company_name=company_name,
        normalized_company=normalize_company_name(company_name) if company_name else None,
        description_text=description,
        location=normalized_location,
        remote_type=remote,
        employment_type=employment,
        seniority=seniority,
        technologies=technologies,
        salary=salary,
        content_hash=hash_value,
        requirements={"technologies": technologies, "seniority": seniority},
    )
