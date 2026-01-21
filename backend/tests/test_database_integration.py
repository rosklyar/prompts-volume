"""Integration tests for database functionality using services."""

import pytest

from src.businessdomain.services import BusinessDomainService
from src.geography.services import CountryService, LanguageService
from src.topics.services import TopicService


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
        name="logistics", description="Logistics and supply chain technology"
    )

    # Create a topic for the new country and domain
    topic = await topic_service.create(
        title="Polish Logistics Topic",
        description="A topic for Polish logistics",
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
    assert topics_by_country[0].title == "Polish Logistics Topic"

    topics_by_domain = await topic_service.get_by_business_domain(domain.id)
    assert len(topics_by_domain) == 1
    assert topics_by_domain[0].title == "Polish Logistics Topic"
