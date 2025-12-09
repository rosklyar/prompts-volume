"""SQLAlchemy ORM models for database tables."""

import enum
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.session import Base


class Language(Base):
    """Language model for internationalization."""

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)

    # Relationships
    country_languages: Mapped[List["CountryLanguage"]] = relationship(
        back_populates="language", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Language(id={self.id}, name='{self.name}', code='{self.code}')>"


class CountryLanguage(Base):
    """Junction table for Country-Language many-to-many relationship with ordering."""

    __tablename__ = "country_languages"

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"),
        primary_key=True
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"),
        primary_key=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    country: Mapped["Country"] = relationship(back_populates="country_languages")
    language: Mapped["Language"] = relationship(back_populates="country_languages")

    # Constraints
    __table_args__ = (
        UniqueConstraint("country_id", "order", name="uq_country_order"),
    )

    def __repr__(self) -> str:
        return f"<CountryLanguage(country_id={self.country_id}, language_id={self.language_id}, order={self.order})>"


class Country(Base):
    """Country model for location/language targeting."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso_code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True, index=True)

    # Relationships
    topics: Mapped[List["Topic"]] = relationship(back_populates="country", cascade="all, delete-orphan")
    country_languages: Mapped[List["CountryLanguage"]] = relationship(
        back_populates="country",
        cascade="all, delete-orphan",
        order_by="CountryLanguage.order"
    )

    @property
    def languages(self) -> List[Language]:
        """Get ordered list of languages for this country."""
        return [cl.language for cl in self.country_languages]

    def __repr__(self) -> str:
        return f"<Country(id={self.id}, name='{self.name}', iso_code='{self.iso_code}')>"


class BusinessDomain(Base):
    """Business domain model for categorizing companies."""

    __tablename__ = "business_domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    topics: Mapped[List["Topic"]] = relationship(back_populates="business_domain", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BusinessDomain(id={self.id}, name='{self.name}')>"


class Topic(Base):
    """Topic model for predefined prompts/categories."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Foreign keys
    business_domain_id: Mapped[int] = mapped_column(
        ForeignKey("business_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    business_domain: Mapped["BusinessDomain"] = relationship(back_populates="topics")
    country: Mapped["Country"] = relationship(back_populates="topics")
    prompts: Mapped[List["Prompt"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, title='{self.title}', business_domain_id={self.business_domain_id}, country_id={self.country_id})>"


class Prompt(Base):
    """Prompt model for storing pre-seeded search prompts with embeddings."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=False)

    # Foreign keys
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    topic: Mapped["Topic"] = relationship(back_populates="prompts")
    evaluations: Mapped[List["PromptEvaluation"]] = relationship(
        back_populates="prompt",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, topic_id={self.topic_id}, prompt_text='{self.prompt_text[:50]}...')>"


class EvaluationStatus(str, enum.Enum):
    """Evaluation status enum."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptEvaluation(Base):
    """Track evaluations of prompts by different AI assistants."""

    __tablename__ = "prompt_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "prompt_id",
            "assistant_name",
            "plan_name",
            name="uq_prompt_assistant_plan"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Assistant and plan identifiers
    assistant_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    plan_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    # Status tracking
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus),
        nullable=False,
        default=EvaluationStatus.IN_PROGRESS,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # Result (JSON with response, citations, timestamp)
    answer: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    prompt: Mapped["Prompt"] = relationship(back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<PromptEvaluation(id={self.id}, prompt_id={self.prompt_id}, assistant_name='{self.assistant_name}', status='{self.status.value}')>"
