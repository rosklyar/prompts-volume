"""Database initialization and seeding logic."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import BusinessDomain, Country, CountryLanguage, Language, Topic


async def seed_initial_data(session: AsyncSession) -> None:
    """
    Seed initial data into the database.
    This function is idempotent - it will only insert data if it doesn't exist.

    Args:
        session: AsyncSession to use for database operations
    """
    # 1. Seed Languages
    await _seed_languages(session)

    # 2. Seed Countries
    await _seed_countries(session)

    # 3. Seed Country-Language mappings
    await _seed_country_languages(session)

    # 4. Seed Business Domains
    await _seed_business_domains(session)

    # 5. Seed Topics (requires countries and business domains)
    await _seed_topics(session)

    await session.commit()


async def _seed_languages(session: AsyncSession) -> None:
    """Seed initial languages (Ukrainian, Russian, English)."""
    # Check if languages already exist
    result = await session.execute(select(Language).where(Language.id.in_([1, 2, 3])))
    existing_languages = result.scalars().all()

    if len(existing_languages) == 0:
        languages = [
            Language(id=1, name="Ukrainian", code="uk"),
            Language(id=2, name="Russian", code="ru"),
            Language(id=3, name="English", code="en"),
        ]
        session.add_all(languages)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('languages_id_seq', (SELECT MAX(id) FROM languages))")
        )


async def _seed_countries(session: AsyncSession) -> None:
    """Seed initial countries."""
    # Check if Ukraine already exists
    result = await session.execute(select(Country).where(Country.iso_code == "UA"))
    existing = result.scalar_one_or_none()

    if existing is None:
        ukraine = Country(
            id=1,
            name="Ukraine",
            iso_code="UA",
        )
        session.add(ukraine)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('countries_id_seq', (SELECT MAX(id) FROM countries))")
        )


async def _seed_country_languages(session: AsyncSession) -> None:
    """Seed country-language mappings (Ukraine -> Ukrainian, Russian)."""
    # Check if mappings already exist
    result = await session.execute(
        select(CountryLanguage).where(CountryLanguage.country_id == 1)
    )
    existing_mappings = result.scalars().all()

    if len(existing_mappings) == 0:
        mappings = [
            CountryLanguage(country_id=1, language_id=1, order=0),  # Ukraine -> Ukrainian (primary)
            CountryLanguage(country_id=1, language_id=2, order=1),  # Ukraine -> Russian (secondary)
        ]
        session.add_all(mappings)
        await session.flush()


async def _seed_business_domains(session: AsyncSession) -> None:
    """Seed initial business domains."""
    # Check if E_COMMERCE already exists
    result = await session.execute(
        select(BusinessDomain).where(BusinessDomain.name == "e-comm")
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        e_commerce = BusinessDomain(
            id=1,
            name="e-comm",
            description="E-commerce is the buying and selling of goods and services over the internet",
        )
        session.add(e_commerce)
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text(
                "SELECT setval('business_domains_id_seq', (SELECT MAX(id) FROM business_domains))"
            )
        )


async def _seed_topics(session: AsyncSession) -> None:
    """Seed initial topics for Ukrainian e-commerce."""
    # Check if topics already exist
    result = await session.execute(select(Topic).where(Topic.id.in_([1, 2])))
    existing_topics = result.scalars().all()

    if len(existing_topics) == 0:
        # Topic 1: Smartphones and phones
        topic1 = Topic(
            id=1,
            title="Смартфони і телефони",
            description="Пошук і покупка телефонів і смартфонів в інтернеті",
            business_domain_id=1,
            country_id=1,
        )

        # Topic 2: Laptops and PCs
        topic2 = Topic(
            id=2,
            title="Ноутбуки та персональні комп'ютери",
            description="Пошук і покупка ноутбуків та персональні комп'ютерів в інтернеті",
            business_domain_id=1,
            country_id=1,
        )

        session.add_all([topic1, topic2])
        await session.flush()

        # Reset sequence to continue from the highest ID
        await session.execute(
            text("SELECT setval('topics_id_seq', (SELECT MAX(id) FROM topics))")
        )
