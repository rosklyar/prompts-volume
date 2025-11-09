"""Integration tests for CompanyMetaInfoService with real OpenAI API calls."""

import os

import pytest
from dotenv import load_dotenv

from src.prompts.company_meta_info_service import (
    CompanyMetaInfo,
    CompanyMetaInfoService,
)

# Load environment variables from .env file
load_dotenv()

@pytest.mark.skip(reason="Integration test - requires OpenAI API key. Run manually.")
@pytest.mark.asyncio
async def test_single_company_detailed():
    """
    Detailed integration test for a single company - useful for debugging.

    To run manually:
        uv run pytest tests/test_company_meta_info_integration.py::test_single_company_detailed -v -s

    Requires:
        - OPENAI_API_KEY environment variable set in .env
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set in environment")

    # Initialize service
    service = CompanyMetaInfoService(api_key=api_key, model="gpt-4o-mini")

    # Test domain (change this to test different companies)
    test_domain = "comfy.ua"

    # Call the service
    meta_info: CompanyMetaInfo = await service.get_meta_info(test_domain)

    assert meta_info.is_ecommerce
