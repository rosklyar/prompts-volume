"""Tests for competitor discovery service."""

from unittest.mock import AsyncMock

import pytest

from src.onboarding.services.competitor_discovery import (
    CompetitorDiscoveryService,
    RawCompetitor,
)


@pytest.fixture
def mock_searcher():
    """Create a mock competitor searcher."""
    searcher = AsyncMock()
    searcher.search = AsyncMock(
        return_value=[
            RawCompetitor(name="Competitor1", domain="competitor1.com"),
            RawCompetitor(name="Competitor2", domain="competitor2.com"),
        ]
    )
    return searcher


@pytest.fixture
def service(mock_searcher):
    """Create a CompetitorDiscoveryService with mocked dependencies."""
    return CompetitorDiscoveryService(searcher=mock_searcher)


@pytest.mark.asyncio
async def test_discover_competitors_returns_competitors_with_empty_variations(
    service, mock_searcher
):
    """Test that service returns competitors with empty variations."""
    result = await service.discover_competitors(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="Ukraine",
    )

    assert len(result) == 2
    assert result[0].brand_name == "Competitor1"
    assert result[0].domain == "competitor1.com"
    assert result[0].variations == []
    assert result[1].brand_name == "Competitor2"
    assert result[1].variations == []

    mock_searcher.search.assert_called_once_with(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="Ukraine",
        num_competitors=5,
    )


@pytest.mark.asyncio
async def test_discover_competitors_empty_when_no_competitors_found(
    service, mock_searcher
):
    """Test that service returns empty list when no competitors found."""
    mock_searcher.search.return_value = []

    result = await service.discover_competitors(
        brand_name="UnknownBrand",
        brand_domain="unknown.com",
        country_name="Ukraine",
    )

    assert result == []


@pytest.mark.asyncio
async def test_discover_competitors_with_custom_num_competitors(
    service, mock_searcher
):
    """Test that num_competitors is passed to searcher."""
    await service.discover_competitors(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="USA",
        num_competitors=10,
    )

    mock_searcher.search.assert_called_once_with(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="USA",
        num_competitors=10,
    )
