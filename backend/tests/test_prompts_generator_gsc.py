"""Tests for PromptsGeneratorService keyword-to-prompt generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.keyword_inspiration.services.prompts_generator_service import PromptsGeneratorService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def service(mock_openai_client):
    """Create a PromptsGeneratorService with mocked client."""
    with patch("src.keyword_inspiration.services.prompts_generator_service.AsyncOpenAI") as mock_class:
        mock_class.return_value = mock_openai_client
        svc = PromptsGeneratorService(api_key="test-key")
        return svc


class TestGeneratePromptsFromKeywords:
    """Tests for generate_prompts_from_keywords method."""

    @pytest.mark.asyncio
    async def test_ecomm_uses_rich_prompt(self, service):
        """Verify e-comm domain uses the rich e-commerce system prompt."""
        keywords = ["best running shoes", "cheap laptops", "wireless headphones"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Which running shoes are best?", "source_keyword": "best running shoes"},
                                {"prompt": "Best laptop deals right now?", "source_keyword": "cheap laptops"},
                                {"prompt": "Best wireless headphones 2025?", "source_keyword": "wireless headphones"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "e-comm", "English")

        assert len(result) == 3
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert result[0] == ("Which running shoes are best?", "best running shoes")

        # Verify e-comm rich prompt was used (has Ukrainian examples and intent understanding)
        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "e-commerce product search prompts" in system_message
        assert "INTENT UNDERSTANDING" in system_message
        assert "Телевізори" in system_message

    @pytest.mark.asyncio
    async def test_fintech_uses_generic_prompt(self, service):
        """Verify fintech domain uses generic template with domain context."""
        keywords = ["best savings account", "high yield savings"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Which savings account is best?", "source_keyword": "best savings account"},
                                {"prompt": "Best high yield savings options?", "source_keyword": "high yield savings"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "fintech", "English")

        assert len(result) == 2

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "fintech" in system_message
        assert "financial services, banking, payments" in system_message
        # Generic prompt should NOT have e-comm-specific content
        assert "Телевізори" not in system_message

    @pytest.mark.asyncio
    async def test_saas_domain(self, service):
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
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "saas", "English")

        assert len(result) == 1

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

        await service.generate_prompts_from_keywords(keywords, "e-comm", "Ukrainian")

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

        await service.generate_prompts_from_keywords(keywords, "e-comm", "Russian")

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

        await service.generate_prompts_from_keywords(keywords, "e-comm", "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "English" in system_message

    @pytest.mark.asyncio
    async def test_unknown_domain_falls_back_to_general(self, service):
        """Verify unknown domains fall back to the general prompt builder."""
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

        await service.generate_prompts_from_keywords(keywords, "custom-domain", "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "general" in system_message
        assert "products, services, and solutions across various industries" in system_message

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

        await service.generate_prompts_from_keywords(keywords, "general", "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "general" in system_message
        assert "products, services, and solutions across various industries" in system_message

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "domain, expected_marker",
        [
            ("saas|crm", "CRM and sales software"),
            ("saas|pm", "project management software"),
            ("saas|marketing", "marketing automation software"),
            ("saas|analytics", "analytics and business intelligence software"),
            ("saas|hr", "HR and people management software"),
        ],
    )
    async def test_saas_subcategory_uses_rich_prompt(self, service, domain, expected_marker):
        """Verify each saas|* subcategory routes to its dedicated prompt."""
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

        await service.generate_prompts_from_keywords(keywords, domain, "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert expected_marker in system_message
        assert "INTENT UNDERSTANDING" in system_message
        assert "EXAMPLE STYLE" in system_message

    @pytest.mark.asyncio
    async def test_bare_saas_still_uses_generic_prompt(self, service):
        """Verify bare 'saas' domain still routes to the generic prompt."""
        keywords = ["project management tools"]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": "Best project management software?", "source_keyword": "project management tools"},
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_prompts_from_keywords(keywords, "saas", "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert "software as a service" in system_message
        # Generic prompt should NOT have subcategory-specific markers
        assert "EXAMPLE STYLE" not in system_message
        assert "INTENT UNDERSTANDING" not in system_message

    @pytest.mark.asyncio
    async def test_keywords_capped_at_20(self, service):
        """Verify keywords are capped at 20."""
        keywords = [f"keyword_{i}" for i in range(30)]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "prompts": [
                                {"prompt": f"Prompt for keyword_{i}", "source_keyword": f"keyword_{i}"}
                                for i in range(20)
                            ]
                        }
                    )
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate_prompts_from_keywords(keywords, "e-comm", "English")

        assert len(result) == 20

        # Verify only first 20 keywords were sent
        call_args = service.client.chat.completions.create.call_args
        user_message = call_args.kwargs["messages"][1]["content"]
        assert "keyword_19" in user_message
        assert "keyword_20" not in user_message
