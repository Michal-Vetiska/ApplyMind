"""Profile and search preference schemas."""

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserProfileOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    technologies: list = []
    experience: list = []
    education: list = []
    languages: list = []
    portfolio_projects: list = []
    preferred_application_language: str = "cs"
    tone_preference: str = "professional_concise"

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    technologies: list | None = None
    experience: list | None = None
    education: list | None = None
    languages: list | None = None
    portfolio_projects: list | None = None
    preferred_application_language: str | None = None
    tone_preference: str | None = None


class SearchProfileOut(BaseModel):
    id: str
    name: str
    enabled: bool
    locations: list
    job_titles: dict
    technologies: list
    employment_types: list
    remote_preferences: list
    minimum_salary: int | None = None
    preferred_salary_min: int | None = None
    preferred_salary_max: int | None = None
    salary_currency: str = "CZK"
    hourly_rate_min: float | None = None
    seniority: list
    exclusion_rules: list
    matching_threshold: float
    auto_apply_enabled: bool
    weight_technology: float
    weight_seniority: float
    weight_location: float
    weight_compensation: float
    weight_other: float

    model_config = {"from_attributes": True}


class SearchProfileCreate(BaseModel):
    name: str
    enabled: bool = True
    locations: list = Field(default_factory=list)
    job_titles: dict = Field(default_factory=dict)
    technologies: list = Field(default_factory=list)
    employment_types: list = Field(default_factory=list)
    remote_preferences: list = Field(default_factory=list)
    minimum_salary: int | None = None
    preferred_salary_min: int | None = None
    preferred_salary_max: int | None = None
    salary_currency: str = "CZK"
    hourly_rate_min: float | None = None
    seniority: list = Field(default_factory=list)
    exclusion_rules: list = Field(default_factory=list)
    matching_threshold: float = 60.0
    auto_apply_enabled: bool = False
    weight_technology: float = 0.35
    weight_seniority: float = 0.20
    weight_location: float = 0.20
    weight_compensation: float = 0.15
    weight_other: float = 0.10


class SearchProfileUpdate(SearchProfileCreate):
    name: str | None = None  # type: ignore[assignment]


class ResumeOut(BaseModel):
    id: str
    name: str
    original_filename: str
    content_type: str
    version: int
    is_default: bool
    enabled: bool
    target_roles: list
    file_hash: str

    model_config = {"from_attributes": True}
