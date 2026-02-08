"""Tests for competitor discovery service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.onboarding.services.competitor_discovery import (
    CompetitorDiscoveryService,
    DiscoveredCompetitor,
    RawCompetitor,
)
from src.onboarding.services.competitor_discovery.openai_client import (
    OpenAIBrandVariationGenerator,
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
def mock_variation_generator():
    """Create a mock variation generator."""
    generator = AsyncMock()
    # Return already-normalized variations (lowercase)
    # since the real generator normalizes internally
    async def generate_batch_impl(brand_names, languages):
        return {
            name: [f"{name.lower()}var", f"{name.lower()}inc"]
            for name in brand_names
        }
    generator.generate_batch = AsyncMock(side_effect=generate_batch_impl)
    return generator


@pytest.fixture
def service(mock_searcher, mock_variation_generator):
    """Create a CompetitorDiscoveryService with mocked dependencies."""
    return CompetitorDiscoveryService(
        searcher=mock_searcher,
        variation_generator=mock_variation_generator,
    )


@pytest.mark.asyncio
async def test_discover_competitors_returns_competitors_with_variations(
    service, mock_searcher, mock_variation_generator
):
    """Test that service returns competitors with variations."""
    result = await service.discover_competitors(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="Ukraine",
        languages=["Ukrainian", "Russian"],
    )

    assert len(result) == 2
    assert result[0].brand_name == "Competitor1"
    assert result[0].domain == "competitor1.com"
    # Variations are normalized lowercase from the generator
    assert "competitor1var" in result[0].variations
    assert "competitor1inc" in result[0].variations
    assert result[1].brand_name == "Competitor2"

    mock_searcher.search.assert_called_once_with(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="Ukraine",
        num_competitors=5,
    )

    # Batch call should be made once with all competitor names
    mock_variation_generator.generate_batch.assert_called_once()
    call_kwargs = mock_variation_generator.generate_batch.call_args[1]
    assert set(call_kwargs["brand_names"]) == {"Competitor1", "Competitor2"}


@pytest.mark.asyncio
async def test_discover_competitors_adds_english_if_missing(
    service, mock_variation_generator
):
    """Test that English is added to languages if missing."""
    await service.discover_competitors(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="Ukraine",
        languages=["Ukrainian"],
    )

    call_kwargs = mock_variation_generator.generate_batch.call_args[1]
    assert "English" in call_kwargs["languages"]


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
        languages=["Ukrainian"],
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
        languages=["English"],
        num_competitors=10,
    )

    mock_searcher.search.assert_called_once_with(
        brand_name="TestBrand",
        brand_domain="testbrand.com",
        country_name="USA",
        num_competitors=10,
    )


class TestVariationNormalization:
    """Tests for the variation normalization logic."""

    @pytest.fixture
    def generator(self):
        """Create generator instance for testing normalization."""
        # We'll test the _normalize_variations method directly
        # Creating with dummy values since we won't make API calls
        gen = object.__new__(OpenAIBrandVariationGenerator)
        return gen

    def test_converts_to_lowercase(self, generator):
        """Test that all variations are converted to lowercase."""
        variations = ["ADIDAS", "Adidas", "AdIdAs", "Адидас", "АДИДАС"]
        result = generator._normalize_variations(variations, "Nike")

        assert all(v == v.lower() for v in result)
        assert "adidas" in result
        assert "адидас" in result

    def test_removes_duplicates_case_insensitive(self, generator):
        """Test that case-insensitive duplicates are removed."""
        variations = ["Nike", "NIKE", "nike", "NiKe"]
        result = generator._normalize_variations(variations, "OriginalBrand")

        assert len(result) == 1
        assert result[0] == "nike"

    def test_limits_to_max_count(self, generator):
        """Test that variations are limited to max_count."""
        variations = ["var1", "var2", "var3", "var4", "var5"]
        result = generator._normalize_variations(variations, "Brand", max_count=3)

        assert len(result) == 3

    def test_excludes_original_brand_name(self, generator):
        """Test that original brand name is excluded."""
        variations = ["Nike", "найк", "NIKE"]
        result = generator._normalize_variations(variations, "Nike")

        assert "nike" not in result
        assert "найк" in result

    def test_removes_suffix_extensions(self, generator):
        """Test that variations with suffix extensions are removed."""
        variations = ["nike", "nikes", "nikeshoes"]
        result = generator._normalize_variations(variations, "Brand")

        assert "nike" in result
        assert "nikes" not in result
        assert "nikeshoes" not in result

    def test_keeps_shorter_root_when_suffix_comes_first(self, generator):
        """Test that shorter root is kept even if suffix comes first."""
        variations = ["nikes", "nike"]
        result = generator._normalize_variations(variations, "Brand")

        # Should keep "nike" and discard "nikes"
        assert "nike" in result
        assert "nikes" not in result

    def test_handles_empty_variations(self, generator):
        """Test handling of empty or whitespace variations."""
        variations = ["", "  ", "valid", "   "]
        result = generator._normalize_variations(variations, "Brand")

        assert result == ["valid"]

    def test_cyrillic_variations_preserved(self, generator):
        """Test that Cyrillic variations are preserved correctly."""
        variations = ["Макдональдс", "макдоналдз", "McDonalds"]
        result = generator._normalize_variations(variations, "McDonald's")

        assert "макдональдс" in result
        assert "макдоналдз" in result
        assert "mcdonalds" in result

    def test_real_world_comfy_case(self, generator):
        """Test the Comfy case that was producing too many variations."""
        # Simulating what the LLM might return
        variations = [
            "Comfy", "comfy", "COMFY",  # Case duplicates
            "Комфи", "комфи",  # Cyrillic duplicates
            "Komfi", "Komfie",  # Invented variations
            "Кофми", "Кофи",  # More invented
            "Kmf", "Kfm", "Komf", "Кмф",  # Random abbreviations
        ]
        result = generator._normalize_variations(variations, "Comfy")

        # Should exclude "comfy" (matches brand name)
        # Should have max 3 variations
        # All should be lowercase
        assert len(result) <= 3
        assert "comfy" not in result  # Excluded - matches brand name
        assert all(v == v.lower() for v in result)


class TestBatchVariationCaseInsensitiveLookup:
    """Tests for case-insensitive key lookup in generate_batch."""

    @pytest.mark.asyncio
    async def test_matches_brand_keys_case_insensitively(self):
        """Test that LLM response keys are matched case-insensitively."""
        # Create a generator with mocked OpenAI client
        generator = object.__new__(OpenAIBrandVariationGenerator)
        generator._model = "test-model"

        # Mock the OpenAI client response
        mock_response = MagicMock()
        # LLM returns lowercase keys, but we pass mixed case brand names
        mock_response.output_text = '{"citrus": ["цитрус"], "MOYO": ["мойо"]}'

        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)
        generator._client = mock_client

        # Call with mixed case brand names
        result = await generator.generate_batch(
            brand_names=["Citrus", "Moyo"],
            languages=["Ukrainian"],
        )

        # Should find variations despite case mismatch
        assert "Citrus" in result
        assert "Moyo" in result
        assert "цитрус" in result["Citrus"]
        assert "мойо" in result["Moyo"]

    @pytest.mark.asyncio
    async def test_prefers_exact_match_over_case_insensitive(self):
        """Test that exact key match is preferred when available."""
        generator = object.__new__(OpenAIBrandVariationGenerator)
        generator._model = "test-model"

        mock_response = MagicMock()
        # LLM returns both exact and different case keys
        mock_response.output_text = '{"Brand": ["exact"], "brand": ["lowercase"]}'

        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)
        generator._client = mock_client

        result = await generator.generate_batch(
            brand_names=["Brand"],
            languages=["English"],
        )

        # Should use exact match "Brand" -> ["exact"]
        assert result["Brand"] == ["exact"]
