"""Tests for PromptsGeneratorService GSC keyword-to-prompt generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.prompts.services.prompts_generator_service import PromptsGeneratorService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def service(mock_openai_client):
    """Create a PromptsGeneratorService with mocked client."""
    with patch("src.prompts.services.prompts_generator_service.AsyncOpenAI") as mock_class:
        mock_class.return_value = mock_openai_client
        svc = PromptsGeneratorService(api_key="test-key")
        return svc


class TestGeneratePromptsFromKeywords:
    """Tests for generate_prompts_from_keywords method."""

    @pytest.mark.asyncio
    async def test_generates_prompts_for_ecommerce(self, service):
        """Verify e-comm domain uses correct template and generates prompts."""
        keywords = ["best running shoes", "cheap laptops", "wireless headphones"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Which running shoes are best?", "source_keyword": "best running shoes"},
                                {"prompt": "Where to buy running shoes?", "source_keyword": "best running shoes"},
                                {"prompt": "Running shoes for beginners?", "source_keyword": "best running shoes"},
                                {"prompt": "Best laptop deals right now?", "source_keyword": "cheap laptops"},
                                {"prompt": "Affordable laptops for students?", "source_keyword": "cheap laptops"},
                                {"prompt": "Which budget laptop is worth it?", "source_keyword": "cheap laptops"},
                                {"prompt": "Best wireless headphones 2025?", "source_keyword": "wireless headphones"},
                                {"prompt": "Wireless vs wired headphones?", "source_keyword": "wireless headphones"},
                                {"prompt": "Headphones for working out?", "source_keyword": "wireless headphones"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "e-comm", "English")

        assert len(result) == 9
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert result[0] == ("Which running shoes are best?", "best running shoes")

        # Verify e-comm domain context was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "e-comm" in system_message
        assert "e-commerce products, online shopping, product recommendations" in system_message

    @pytest.mark.asyncio
    async def test_generates_prompts_for_general_domains(self, service):
        """Verify fintech, saas, etc. use general template with domain context."""
        keywords = ["best savings account", "high yield savings"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Which savings account is best?", "source_keyword": "best savings account"},
                                {"prompt": "Compare savings accounts rates?", "source_keyword": "best savings account"},
                                {"prompt": "How to maximize savings?", "source_keyword": "best savings account"},
                                {"prompt": "Best high yield savings options?", "source_keyword": "high yield savings"},
                                {"prompt": "High yield vs regular savings?", "source_keyword": "high yield savings"},
                                {"prompt": "Where to open high yield account?", "source_keyword": "high yield savings"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "fintech", "English")

        assert len(result) == 6

        # Verify general template was used with fintech context
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "fintech" in system_message
        assert "financial services, banking, payments" in system_message

    @pytest.mark.asyncio
    async def test_generates_prompts_for_saas_domain(self, service):
        """Verify SaaS domain uses appropriate context."""
        keywords = ["project management tools"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Best project management software?", "source_keyword": "project management tools"},
                                {"prompt": "Asana vs Monday comparison?", "source_keyword": "project management tools"},
                                {"prompt": "Tool for team collaboration?", "source_keyword": "project management tools"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "saas", "English")

        assert len(result) == 3

        # Verify SaaS context
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "saas" in system_message
        assert "software as a service" in system_message

    @pytest.mark.asyncio
    async def test_empty_keywords_raises(self, service):
        """Verify empty keywords list raises ValueError."""
        with pytest.raises(ValueError, match="Keywords list cannot be empty"):
            await service.generate_prompts_from_keywords([], "e-comm", "English")

    @pytest.mark.asyncio
    async def test_language_passed_ukrainian(self, service):
        """Verify Ukrainian language is used when passed as parameter."""
        keywords = ["найкращі телефони", "де їх купити"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Які телефони краще?", "source_keyword": "найкращі телефони"},
                                {"prompt": "Де їх купити?", "source_keyword": "де їх купити"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "e-comm", "Ukrainian", prompts_per_keyword=1)

        # Verify Ukrainian was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "Ukrainian" in system_message

    @pytest.mark.asyncio
    async def test_language_passed_russian(self, service):
        """Verify Russian language is used when passed as parameter."""
        keywords = ["лучший смартфон", "где купить ноутбук"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Какой смартфон лучше?", "source_keyword": "лучший смартфон"},
                                {"prompt": "Где купить ноутбук?", "source_keyword": "где купить ноутбук"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "e-comm", "Russian", prompts_per_keyword=1)

        # Verify Russian was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "Russian" in system_message

    @pytest.mark.asyncio
    async def test_language_passed_english(self, service):
        """Verify English language is used when passed as parameter."""
        keywords = ["best smartphone", "where to buy laptop"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Which smartphone is best?", "source_keyword": "best smartphone"},
                                {"prompt": "Where to buy laptop?", "source_keyword": "where to buy laptop"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "e-comm", "English", prompts_per_keyword=1)

        # Verify English was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "English" in system_message

    @pytest.mark.asyncio
    async def test_custom_prompts_per_keyword(self, service):
        """Verify prompts_per_keyword parameter is respected in prompt."""
        keywords = ["test keyword"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Prompt 1", "source_keyword": "test keyword"},
                                {"prompt": "Prompt 2", "source_keyword": "test keyword"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "e-comm", "English", prompts_per_keyword=2)

        # Verify prompts_per_keyword was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "Prompts per keyword: 2" in system_message

    @pytest.mark.asyncio
    async def test_unknown_domain_uses_generic_context(self, service):
        """Verify unknown domains get a generic context string."""
        keywords = ["test keyword"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Test prompt", "source_keyword": "test keyword"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "custom-domain", "English", prompts_per_keyword=1)

        # Verify generic context was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "custom-domain services and solutions" in system_message

    @pytest.mark.asyncio
    async def test_general_domain_uses_broad_context(self, service):
        """Verify 'general' domain uses broad context for any business type."""
        keywords = ["best solution for my needs"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "What's the best solution?", "source_keyword": "best solution for my needs"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "general", "English", prompts_per_keyword=1)

        # Verify general context was used
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "general" in system_message
        assert "products, services, and solutions across various industries" in system_message
