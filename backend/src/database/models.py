"""SQLAlchemy ORM models for database tables."""

import enum
import uuid as uuid_module
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.session import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid_module.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', is_superuser={self.is_superuser})>"


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
    topic_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
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


class PriorityPromptQueue(Base):
    """Queue for priority prompts that should be evaluated first."""

    __tablename__ = "priority_prompt_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Each prompt can only be in queue once
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,  # For ordering by priority (FIFO within priority)
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # For querying all prompts from same request
    )

    # Relationship
    prompt: Mapped["Prompt"] = relationship()

    def __repr__(self) -> str:
        return f"<PriorityPromptQueue(id={self.id}, prompt_id={self.prompt_id}, request_id='{self.request_id}')>"


class EvaluationStatus(str, enum.Enum):
    """Evaluation status enum."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptEvaluation(Base):
    """Track evaluations of prompts by different AI assistants.

    Note: Multiple evaluations can exist for the same (prompt_id, assistant_plan_id)
    combination to support retry scenarios when evaluations timeout or fail.
    """

    __tablename__ = "prompt_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Assistant plan identifier (references ai_assistant_plans)
    assistant_plan_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistant_plans.id", ondelete="CASCADE"),
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
    assistant_plan: Mapped["AIAssistantPlan"] = relationship(back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<PromptEvaluation(id={self.id}, prompt_id={self.prompt_id}, assistant_plan_id={self.assistant_plan_id}, status='{self.status.value}')>"


class AIAssistant(Base):
    """AI Assistant model for tracking supported assistants."""

    __tablename__ = "ai_assistants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,  # Index for efficient case-insensitive lookups
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    plans: Mapped[List["AIAssistantPlan"]] = relationship(
        back_populates="assistant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AIAssistant(id={self.id}, name='{self.name}')>"


class AIAssistantPlan(Base):
    """AI Assistant Plan model for tracking supported plans per assistant."""

    __tablename__ = "ai_assistant_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # Index for efficient lookups
    )
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    assistant: Mapped["AIAssistant"] = relationship(back_populates="plans")
    evaluations: Mapped[List["PromptEvaluation"]] = relationship(
        back_populates="assistant_plan",
        cascade="all, delete-orphan"
    )

    # Constraints - ensure unique plan names per assistant
    __table_args__ = (
        UniqueConstraint("assistant_id", "name", name="uq_assistant_plan"),
    )

    def __repr__(self) -> str:
        return f"<AIAssistantPlan(id={self.id}, assistant_id={self.assistant_id}, name='{self.name}')>"
