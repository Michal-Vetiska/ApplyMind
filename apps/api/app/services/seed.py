"""Bootstrap admin user, profile, and default search profile."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.auth import UserAccount
from app.models.profile import SearchProfile, UserProfile
from app.models.settings import AppSettings

logger = get_logger(__name__)

DEFAULT_TECHNOLOGIES = [
    "React",
    "React Native",
    "Expo",
    "Vue.js",
    "TypeScript",
    "JavaScript",
    "HTML",
    "CSS",
    "PHP",
    "Laravel",
    "REST APIs",
    "PostgreSQL",
    "Supabase",
    "Docker",
    "Linux",
    "Git",
    "GitHub Actions",
    "CI/CD",
    "Netlify",
    "Vercel",
    "Cursor",
    "LLM API integrations",
    "Python",
]

DEFAULT_EXPERIENCE = [
    {
        "company": "Synot Tech",
        "role": "Backend Developer",
        "highlights": [
            "Backend development",
            "Internal applications",
            "API development",
            "CI/CD",
            "Docker",
            "Infrastructure work",
        ],
        "approved": False,
        "note": "Seed data — verify and approve before using as evidence",
    },
    {
        "company": "OtelApps",
        "role": "Co-founder / CTO",
        "highlights": [
            "React Native mobile application",
            "React administration interface",
            "Laravel backend",
            "Supabase PostgreSQL",
            "Hospitality software",
        ],
        "approved": False,
        "note": "Seed data — verify and approve before using as evidence",
    },
]

DEFAULT_PORTFOLIO = [
    {"name": "OtelApps", "url": "https://otelapps.com/", "approved": False},
    {
        "name": "Los Santos Detail",
        "url": "https://lossantosdetail.netlify.app/",
        "approved": False,
    },
    {
        "name": "Los Santos Rental",
        "url": "https://lossantosrental.netlify.app/",
        "approved": False,
    },
    {"name": "Flexic Scar Care", "url": "https://flexicscarcare.eu/", "approved": False},
]


async def seed_defaults(db: AsyncSession) -> None:
    settings = get_settings()

    result = await db.execute(
        select(UserAccount).where(UserAccount.email == settings.admin_email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = UserAccount(
            email=settings.admin_email.lower(),
            password_hash=hash_password(settings.admin_password),
            name=settings.admin_name,
        )
        db.add(user)
        logger.info("seeded_admin_user", email=settings.admin_email)

    profile_result = await db.execute(select(UserProfile).limit(1))
    if profile_result.scalar_one_or_none() is None:
        db.add(
            UserProfile(
                name=settings.admin_name,
                email=settings.admin_email,
                location="Praha 4 - Krč, Czech Republic",
                portfolio_url="https://otelapps.com/",
                technologies=DEFAULT_TECHNOLOGIES,
                experience=DEFAULT_EXPERIENCE,
                portfolio_projects=DEFAULT_PORTFOLIO,
                languages=[{"language": "Czech", "level": "native"}, {"language": "English", "level": "B2+"}],
                preferred_application_language="cs",
                summary=(
                    "Software developer based in Prague focusing on React, React Native, "
                    "Laravel/PHP, and modern full-stack delivery. Seed profile — edit before use."
                ),
            )
        )
        logger.info("seeded_user_profile")

    search_result = await db.execute(select(SearchProfile).limit(1))
    if search_result.scalar_one_or_none() is None:
        db.add(
            SearchProfile(
                name="Primary IT Search",
                enabled=True,
                locations=["Praha", "Praha 4", "Czech Republic remote", "Hybrid Prague"],
                job_titles={
                    "high": [
                        "React Developer",
                        "Vue Developer",
                        "Frontend Developer",
                        "TypeScript Developer",
                        "React Native Developer",
                        "PHP Developer",
                        "Laravel Developer",
                        "Fullstack Developer",
                        "Junior AI Developer",
                        "AI Engineer",
                    ],
                    "medium": [
                        "IT Support",
                        "Application Support",
                        "Junior DevOps",
                        "QA Engineer",
                        "Software Tester",
                        "Technical Support Engineer",
                        "Junior System Administrator",
                    ],
                    "optional": [
                        "Technical IT internship",
                        "IT contract project",
                        "Paid freelance development",
                    ],
                },
                technologies=DEFAULT_TECHNOLOGIES,
                employment_types=[
                    "full_time",
                    "part_time",
                    "dpc",
                    "dpp",
                    "contract",
                    "ico",
                ],
                remote_preferences=["onsite_prague", "hybrid_prague", "remote_cz"],
                minimum_salary=40000,
                preferred_salary_min=50000,
                preferred_salary_max=70000,
                salary_currency="CZK",
                seniority=["junior", "junior_medior", "medior", "practical_equivalent"],
                exclusion_rules=[
                    "senior_management_unrelated",
                    "mandatory_certifications_not_held",
                    "incompatible_specialist",
                ],
                matching_threshold=60.0,
                auto_apply_enabled=False,
            )
        )
        logger.info("seeded_search_profile")

    settings_result = await db.execute(
        select(AppSettings).where(AppSettings.key == "privacy")
    )
    if settings_result.scalar_one_or_none() is None:
        db.add(
            AppSettings(
                key="privacy",
                value={
                    "allow_llm_on_historical_mail": False,
                    "minimize_unrelated_email_storage": True,
                    "auto_delete_non_recruitment": False,
                },
            )
        )
        db.add(
            AppSettings(
                key="automation",
                value={
                    "discover_jobs_hours": 3,
                    "sync_inbox_minutes": 10,
                    "followup_days": 7,
                    "email_dry_run": True,
                    "email_sending_enabled": False,
                },
            )
        )
        logger.info("seeded_app_settings")

    await db.commit()
