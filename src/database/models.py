"""SQLAlchemy ORM models for database tables."""

from typing import List

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
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

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, title='{self.title}', business_domain_id={self.business_domain_id}, country_id={self.country_id})>"
