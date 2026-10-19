"""Application-wide settings stored in the database."""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AppSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
