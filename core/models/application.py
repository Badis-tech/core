"""Application model."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from core.models.job import Job


class ApplicationStatus(str, enum.Enum):
    """Application status options."""

    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class Application(Base, TimestampMixin):
    """Job application tracking model."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application {self.id} - {self.status.value}>"
