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

    def test_detect_single_brand_single_mention(self):
        """Test detecting a single mention of a single brand."""
        brands = [BrandInput(name="Moyo", variations=["Moyo"])]
        text = "Check out Moyo for best deals"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        assert result[0].brand_name == "Moyo"
        assert len(result[0].mentions) == 1
        assert result[0].mentions[0].start == 10
        assert result[0].mentions[0].end == 14
        assert result[0].mentions[0].matched_text == "Moyo"
        assert result[0].mentions[0].variation == "Moyo"

    def test_detect_single_brand_multiple_mentions(self):
        """Test detecting multiple mentions of the same brand."""
        brands = [BrandInput(name="Moyo", variations=["Moyo"])]
        text = "Moyo has great prices. Visit Moyo today!"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        assert result[0].brand_name == "Moyo"
        assert len(result[0].mentions) == 2
        assert result[0].mentions[0].start == 0
        assert result[0].mentions[1].start == 29

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

    def test_detect_multiple_variations_same_brand(self):
        """Test detecting multiple variations of the same brand."""
        brands = [
            BrandInput(name="Moyo", variations=["Moyo", "Мойо", "moyo.ua"])
        ]
        text = "Moyo (Мойо) at moyo.ua"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        # Note: "Moyo" also matches "moyo" in "moyo.ua" (case-insensitive)
        # so we get 4 matches: "Moyo", "Мойо", "moyo" (from Moyo variation), "moyo.ua"
        assert len(result[0].mentions) == 4
        matched_texts = [m.matched_text for m in result[0].mentions]
        assert "Moyo" in matched_texts
        assert "Мойо" in matched_texts
        assert "moyo.ua" in matched_texts

    def test_detect_sorted_by_position(self):
        """Test that mentions are sorted by start position."""
        brands = [
            BrandInput(name="Moyo", variations=["Moyo", "Мойо"])
        ]
        text = "Мойо first, then Moyo"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        mentions = result[0].mentions
        assert mentions[0].matched_text == "Мойо"
        assert mentions[1].matched_text == "Moyo"
        assert mentions[0].start < mentions[1].start

    def test_detect_empty_text(self):
        """Test with empty text."""
        brands = [BrandInput(name="Moyo", variations=["Moyo"])]
        text = ""

        result = self.detector.detect(text, brands)

        assert result == []

    def test_detect_empty_brands(self):
        """Test with empty brands list."""
        brands = []
        text = "Some text with Moyo"

        result = self.detector.detect(text, brands)

        assert result == []

    def test_detect_no_matches(self):
        """Test when no brands are found in text."""
        brands = [BrandInput(name="Moyo", variations=["Moyo"])]
        text = "This text has no matching brands"

        result = self.detector.detect(text, brands)

        assert result == []

    def test_detect_special_characters_in_variation(self):
        """Test variations with special regex characters."""
        brands = [
            BrandInput(name="Test", variations=["test.com", "test[1]", "test+plus"])
        ]
        text = "Visit test.com or test[1] or test+plus"

        result = self.detector.detect(text, brands)

        assert len(result) == 1
        assert len(result[0].mentions) == 3

    def test_detect_overlapping_variations_different_brands(self):
        """Test handling of overlapping text that matches different brands."""
        brands = [
            BrandInput(name="Brand1", variations=["shop"]),
            BrandInput(name="Brand2", variations=["shopping"]),
        ]
        text = "Go shopping at the shop"

        result = self.detector.detect(text, brands)

        # Both brands should be detected
        brand_names = [r.brand_name for r in result]
        assert "Brand1" in brand_names
        assert "Brand2" in brand_names
