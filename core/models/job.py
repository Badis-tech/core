"""Job model and related enums."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, TimestampMixin, generate_uuid


class JobSource(str, enum.Enum):
    """Job board sources."""

    BUNDESAGENTUR = "bundesagentur"
    REMOTEOK = "remoteok"
    USAJOBS = "usajobs"
    ARBETSFORMEDLINGEN = "arbetsformedlingen"
    FRANCE_TRAVAIL = "france_travail"
    ADZUNA = "adzuna"
    REMOTIVE = "remotive"
    ARBEITNOW = "arbeitnow"


class RemoteType(str, enum.Enum):
    """Remote work options."""

    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class EmploymentType(str, enum.Enum):
    """Employment type options."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class Job(Base, TimestampMixin):
    """Job listing model."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[JobSource] = mapped_column(Enum(JobSource), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    company_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("companies.id"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[RemoteType | None] = mapped_column(Enum(RemoteType), nullable=True)
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(EmploymentType), nullable=True
    )

    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    company: Mapped["Company | None"] = relationship("Company", back_populates="jobs")
    skills: Mapped[list["JobSkill"]] = relationship("JobSkill", back_populates="job")
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="job")

    def __repr__(self) -> str:
        return f"<Job {self.title} at {self.company_name}>"


# Import for type hints
from core.models.application import Application  # noqa: E402
from core.models.company import Company  # noqa: E402
from core.models.skill import JobSkill  # noqa: E402
