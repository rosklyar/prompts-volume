"""SQLAlchemy ORM models for prompts_db tables."""

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
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
    topic_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    topic: Mapped["Topic"] = relationship(back_populates="prompts")

    def __repr__(self) -> str:
        return f"<Prompt(id={self.id}, topic_id={self.topic_id}, prompt_text='{self.prompt_text[:50]}...')>"


class PromptGroup(Base):
    """User-owned group for organizing prompts."""

    __tablename__ = "prompt_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - user is in users_db
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    brands: Mapped[Optional[List[dict]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Brand/company tracking with variations"
    )

    # Relationships
    bindings: Mapped[List["PromptGroupBinding"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan"
    )

    # Constraints - unique title per user
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uq_prompt_groups_user_title"),
    )

    def __repr__(self) -> str:
        return f"<PromptGroup(id={self.id}, user_id='{self.user_id}', title='{self.title}')>"


class PromptGroupBinding(Base):
    """Junction table linking prompts to groups.

    A prompt can belong to multiple groups for the same user.
    """

    __tablename__ = "prompt_group_bindings"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    group: Mapped["PromptGroup"] = relationship(back_populates="bindings")
    prompt: Mapped["Prompt"] = relationship()

    # Constraints - each prompt can only be in a group once
    __table_args__ = (
        UniqueConstraint("group_id", "prompt_id", name="uq_prompt_group_bindings_group_prompt"),
    )

    def __repr__(self) -> str:
        return f"<PromptGroupBinding(id={self.id}, group_id={self.group_id}, prompt_id={self.prompt_id})>"
