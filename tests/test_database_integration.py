"""Integration tests for database functionality using services."""

import pytest

from src.prompts.services.business_domain_service import BusinessDomainService
from src.prompts.services.country_service import CountryService
from src.prompts.services.language_service import LanguageService
from src.prompts.services.topic_service import TopicService


@pytest.mark.asyncio
async def test_country_service_get_by_iso_code(country_service: CountryService):
    """Test that we can get a country by ISO code using CountryService."""
    ukraine = await country_service.get_by_iso_code("UA")

    assert ukraine is not None, "Ukraine should be seeded"
    assert ukraine.id == 1
    assert ukraine.name == "Ukraine"
    assert ukraine.iso_code == "UA"


@pytest.mark.asyncio
async def test_country_service_get_all(country_service: CountryService):
    """Test that we can get all countries using CountryService."""
    countries = await country_service.get_all()

    assert len(countries) >= 1, "Should have at least 1 country (Ukraine)"
    assert any(c.iso_code == "UA" for c in countries)


@pytest.mark.asyncio
async def test_country_service_create(country_service: CountryService):
    """Test creating a new country using CountryService."""
    new_country = await country_service.create(name="United States", iso_code="US")

    assert new_country.id is not None
    assert new_country.name == "United States"
    assert new_country.iso_code == "US"

    # Verify it was saved
    retrieved = await country_service.get_by_iso_code("US")
    assert retrieved is not None
    assert retrieved.name == "United States"


@pytest.mark.asyncio
async def test_language_service_get_by_code(language_service: LanguageService):
    """Test that we can get a language by ISO code using LanguageService."""
    ukrainian = await language_service.get_by_code("uk")

    assert ukrainian is not None, "Ukrainian should be seeded"
    assert ukrainian.id == 1
    assert ukrainian.name == "Ukrainian"
    assert ukrainian.code == "uk"


@pytest.mark.asyncio
async def test_language_service_get_all(language_service: LanguageService):
    """Test that we can get all languages using LanguageService."""
    languages = await language_service.get_all()

    assert len(languages) >= 3, "Should have at least 3 languages (Ukrainian, Russian, English)"
    codes = [lang.code for lang in languages]
    assert "uk" in codes
    assert "ru" in codes
    assert "en" in codes


@pytest.mark.asyncio
async def test_language_service_create(language_service: LanguageService):
    """Test creating a new language using LanguageService."""
    new_language = await language_service.create(name="Spanish", code="es")

    assert new_language.id is not None
    assert new_language.name == "Spanish"
    assert new_language.code == "es"

    # Verify it was saved
    retrieved = await language_service.get_by_code("es")
    assert retrieved is not None
    assert retrieved.name == "Spanish"


@pytest.mark.asyncio
async def test_country_with_ordered_languages(country_service: CountryService):
    """Test that Country returns languages in correct order."""
    ukraine = await country_service.get_by_iso_code("UA")

    assert ukraine is not None
    languages = ukraine.languages
    assert len(languages) == 2, "Ukraine should have 2 languages"
    assert languages[0].name == "Ukrainian", "First language should be Ukrainian (order=0)"
    assert languages[1].name == "Russian", "Second language should be Russian (order=1)"


@pytest.mark.asyncio
async def test_business_domain_service_get_by_name(
    business_domain_service: BusinessDomainService,
):
    """Test that we can get a business domain by name using BusinessDomainService."""
    e_commerce = await business_domain_service.get_by_name("e-comm")

    assert e_commerce is not None, "E_COMMERCE business domain should be seeded"
    assert e_commerce.id == 1
    assert e_commerce.name == "e-comm"
    assert (
        e_commerce.description
        == "E-commerce is the buying and selling of goods and services over the internet"
    )


@pytest.mark.asyncio
async def test_business_domain_service_get_all(
    business_domain_service: BusinessDomainService,
):
    """Test that we can get all business domains using BusinessDomainService."""
    domains = await business_domain_service.get_all()

    assert len(domains) >= 1, "Should have at least 1 business domain (e-comm)"
    assert any(d.name == "e-comm" for d in domains)


@pytest.mark.asyncio
async def test_business_domain_service_create(
    business_domain_service: BusinessDomainService,
):
    """Test creating a new business domain using BusinessDomainService."""
    new_domain = await business_domain_service.create(
        name="saas", description="Software as a Service companies"
    )

    assert new_domain.id is not None
    assert new_domain.name == "saas"
    assert new_domain.description == "Software as a Service companies"

    # Verify it was saved
    retrieved = await business_domain_service.get_by_name("saas")
    assert retrieved is not None
    assert retrieved.description == "Software as a Service companies"


@pytest.mark.asyncio
async def test_topic_service_get_all(topic_service: TopicService):
    """Test that initial topics are seeded using TopicService."""
    topics = await topic_service.get_all()

    assert len(topics) == 2, "Should have 2 initial topics"

    # Find topics by title
    smartphones_topic = next((t for t in topics if "Смартфони" in t.title), None)
    laptops_topic = next((t for t in topics if "Ноутбуки" in t.title), None)

    assert smartphones_topic is not None
    assert smartphones_topic.title == "Смартфони і телефони"
    assert smartphones_topic.business_domain_id == 1
    assert smartphones_topic.country_id == 1

    assert laptops_topic is not None
    assert laptops_topic.title == "Ноутбуки та персональні комп'ютери"
    assert laptops_topic.business_domain_id == 1
    assert laptops_topic.country_id == 1


@pytest.mark.asyncio
async def test_topic_service_get_by_id(topic_service: TopicService):
    """Test getting a topic by ID using TopicService."""
    topic = await topic_service.get_by_id(1)

    assert topic is not None
    assert topic.id == 1
    assert topic.title == "Смартфони і телефони"
    assert topic.description == "Пошук і покупка телефонів і смартфонів в інтернеті"


@pytest.mark.asyncio
async def test_topic_service_get_by_country(topic_service: TopicService):
    """Test getting topics by country using TopicService."""
    topics = await topic_service.get_by_country(country_id=1)

    assert len(topics) == 2, "Ukraine should have 2 topics"
    assert all(t.country_id == 1 for t in topics)


@pytest.mark.asyncio
async def test_topic_service_get_by_business_domain(topic_service: TopicService):
    """Test getting topics by business domain using TopicService."""
    topics = await topic_service.get_by_business_domain(business_domain_id=1)

    assert len(topics) == 2, "E-commerce should have 2 topics"
    assert all(t.business_domain_id == 1 for t in topics)


@pytest.mark.asyncio
async def test_topic_service_create(topic_service: TopicService):
    """Test creating a new topic using TopicService."""
    new_topic = await topic_service.create(
        title="Тестова тема",
        description="Тестовий опис теми",
        business_domain_id=1,
        country_id=1,
    )

    assert new_topic.id is not None
    assert new_topic.title == "Тестова тема"
    assert new_topic.description == "Тестовий опис теми"
    assert new_topic.business_domain_id == 1
    assert new_topic.country_id == 1

    # Verify it was saved
    retrieved = await topic_service.get_by_id(new_topic.id)
    assert retrieved is not None
    assert retrieved.title == "Тестова тема"


@pytest.mark.asyncio
async def test_services_integration(
    country_service: CountryService,
    business_domain_service: BusinessDomainService,
    topic_service: TopicService,
):
    """Test creating related entities across all services."""
    # Create a new country
    country = await country_service.create(name="Poland", iso_code="PL")

    # Create a new business domain
    domain = await business_domain_service.create(
        name="fintech", description="Financial technology companies"
    )

    # Create a topic for the new country and domain
    topic = await topic_service.create(
        title="Polish Fintech Topic",
        description="A topic for Polish fintech",
        business_domain_id=domain.id,
        country_id=country.id,
    )

    # Verify relationships
    assert topic.country_id == country.id
    assert topic.business_domain_id == domain.id

    # Verify we can retrieve via services
    retrieved_topic = await topic_service.get_by_id(topic.id)
    assert retrieved_topic is not None

    topics_by_country = await topic_service.get_by_country(country.id)
    assert len(topics_by_country) == 1
    assert topics_by_country[0].title == "Polish Fintech Topic"

    topics_by_domain = await topic_service.get_by_business_domain(domain.id)
    assert len(topics_by_domain) == 1
    assert topics_by_domain[0].title == "Polish Fintech Topic"
