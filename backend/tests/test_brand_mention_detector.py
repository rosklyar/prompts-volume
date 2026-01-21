"""Unit tests for BrandMentionDetector service."""

import pytest

from src.reports.services.brand_mention_detector import (
    BrandInput,
    BrandMentionDetector,
)


class TestBrandMentionDetector:
    """Tests for BrandMentionDetector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = BrandMentionDetector()

    def test_detect_multiple_brands(self):
        """Test detecting multiple brands in text."""
        brands = [
            BrandInput(name="Moyo", variations=["Moyo"]),
            BrandInput(name="Rozetka", variations=["Rozetka"]),
        ]
        text = "Compare Moyo and Rozetka prices"

        result = self.detector.detect(text, brands)

        assert len(result) == 2
        brand_names = [r.brand_name for r in result]
        assert "Moyo" in brand_names
        assert "Rozetka" in brand_names

    def test_detect_cyrillic_variations(self):
        """Test detecting Cyrillic brand variations."""
        brands = [BrandInput(name="Moyo", variations=["Moyo", "Мойо"])]
        text = "Магазин Мойо пропонує найкращі ціни"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        assert result[0].brand_name == "Moyo"
        assert len(result[0].mentions) == 1
        assert result[0].mentions[0].matched_text == "Мойо"
        assert result[0].mentions[0].variation == "Мойо"

    def test_detect_case_insensitive(self):
        """Test case-insensitive matching."""
        brands = [BrandInput(name="Rozetka", variations=["rozetka.com.ua"])]
        text = "Visit ROZETKA.COM.UA for deals"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        assert result[0].mentions[0].matched_text == "ROZETKA.COM.UA"
        assert result[0].mentions[0].variation == "rozetka.com.ua"
