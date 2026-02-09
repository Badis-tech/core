"""Company model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from core.models.job import Job


class Company(Base):
    """Company model for job listings."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company {self.name}>"

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize company name for deduplication."""
        return name.lower().strip()
