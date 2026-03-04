"""Tests for PromptsGeneratorService keyword-to-prompt generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.keyword_inspiration.domain_prompts import _render_template, build_system_prompt
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


def _mock_session():
    """Create a mock AsyncSession."""
    return AsyncMock()


def _openai_response(prompts_data: list[dict]) -> MagicMock:
    """Build a mock OpenAI chat response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({"prompts": prompts_data})
            )
        )
    ]
    return mock_response


class TestRenderTemplate:
    """Unit tests for _render_template."""

    def test_basic_placeholder_substitution(self):
        template = "Keywords: {keywords}, Count: {keywords_count}, Lang: {language}, Domain: {domain_name}"
        result = _render_template(template, ["a", "b"], "English", "saas")
        assert result == "Keywords: a, b, Count: 2, Lang: English, Domain: saas"

    def test_json_braces_preserved(self):
        """Double braces {{ in templates survive format_map as literal braces."""
        template = '{{"prompt": "test", "kw": "{keywords}"}}'
        result = _render_template(template, ["x"], "English", "test")
        assert result == '{"prompt": "test", "kw": "x"}'


class TestBuildSystemPrompt:
    """Tests for build_system_prompt DB lookup + fallback."""

    @pytest.mark.asyncio
    async def test_uses_db_template_when_found(self):
        session = _mock_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "DB template: {keywords} in {language}"
        session.execute.return_value = mock_result

        result = await build_system_prompt(session, "saas", ["kw1"], "English")
        assert result == "DB template: kw1 in English"

    @pytest.mark.asyncio
    async def test_uses_fallback_when_not_found(self):
        session = _mock_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        result = await build_system_prompt(session, "unknown-domain", ["kw1"], "English")
        assert "unknown-domain" in result
        assert "kw1" in result
        assert "English" in result


class TestGeneratePromptsFromKeywords:
    """Tests for generate_prompts_from_keywords method."""

    @pytest.mark.asyncio
    async def test_calls_build_system_prompt_and_openai(self, service):
        """Service calls build_system_prompt, passes result to OpenAI."""
        session = _mock_session()
        keywords = ["best running shoes", "cheap laptops"]

        service.client.chat.completions.create = AsyncMock(
            return_value=_openai_response([
                {"prompt": "Which running shoes are best?", "source_keyword": "best running shoes"},
                {"prompt": "Best laptop deals?", "source_keyword": "cheap laptops"},
            ])
        )

        with patch(
            "src.keyword_inspiration.services.prompts_generator_service.build_system_prompt",
            new_callable=AsyncMock,
            return_value="MOCKED SYSTEM PROMPT",
        ) as mock_build:
            result = await service.generate_prompts_from_keywords(
                keywords, "e-comm", "English", session=session
            )

        assert len(result) == 2
        assert result[0] == ("Which running shoes are best?", "best running shoes")

        mock_build.assert_awaited_once_with(session, "e-comm", keywords, "English")

        call_args = service.client.chat.completions.create.call_args
        system_message = call_args.kwargs["messages"][0]["content"]
        assert system_message == "MOCKED SYSTEM PROMPT"

    @pytest.mark.asyncio
    async def test_empty_keywords_raises(self, service):
        """Verify empty keywords list raises ValueError."""
        session = _mock_session()
        with pytest.raises(ValueError, match="Keywords list cannot be empty"):
            await service.generate_prompts_from_keywords([], "e-comm", "English", session=session)

    @pytest.mark.asyncio
    async def test_keywords_capped_at_20(self, service):
        """Verify keywords are capped at 20."""
        session = _mock_session()
        keywords = [f"keyword_{i}" for i in range(30)]

        service.client.chat.completions.create = AsyncMock(
            return_value=_openai_response([
                {"prompt": f"Prompt for keyword_{i}", "source_keyword": f"keyword_{i}"}
                for i in range(20)
            ])
        )

        with patch(
            "src.keyword_inspiration.services.prompts_generator_service.build_system_prompt",
            new_callable=AsyncMock,
            return_value="MOCKED",
        ):
            result = await service.generate_prompts_from_keywords(
                keywords, "e-comm", "English", session=session
            )

        assert len(result) == 20

        call_args = service.client.chat.completions.create.call_args
        user_message = call_args.kwargs["messages"][1]["content"]
        assert "keyword_19" in user_message
        assert "keyword_20" not in user_message
