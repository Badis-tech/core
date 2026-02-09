"""Skill models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from core.models.job import Job


class Skill(Base):
    """Skill model for job requirements."""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    jobs: Mapped[list["JobSkill"]] = relationship("JobSkill", back_populates="skill")

    def __repr__(self) -> str:
        return f"<Skill {self.name}>"


class JobSkill(Base):
    """Association table between jobs and skills."""

    __tablename__ = "job_skills"

    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="jobs")
