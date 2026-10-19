"""ApplyMind FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.api import applications as applications_api
from app.api import analytics as analytics_api
from app.api import automations as automations_api
from app.api import email as email_api
from app.api import jobs as jobs_api
from app.api import knowledge as knowledge_api
from app.api import profile as profile_api
from app.api import settings as settings_api
from app.api import sources as sources_api
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import AsyncSessionLocal
from app.services.seed import seed_defaults

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    for sub in ("uploads", "resumes", "knowledge"):
        Path(settings.data_dir, sub).mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        try:
            await seed_defaults(db)
        except Exception as exc:
            logger.warning("seed_failed", error=str(exc))

    logger.info("app_started", env=settings.app_env)
    yield
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(profile_api.router)
    application.include_router(jobs_api.router)
    application.include_router(sources_api.router)
    application.include_router(applications_api.router)
    application.include_router(email_api.router)
    application.include_router(knowledge_api.router)
    application.include_router(analytics_api.router)
    application.include_router(automations_api.router)
    application.include_router(settings_api.router)

    return application


app = create_app()
