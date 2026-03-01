"""Base protocol and generic builder for domain prompt generation."""

from typing import Protocol


class DomainPromptBuilder(Protocol):
    """Protocol for domain-specific prompt builders."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str: ...


class GenericDomainPromptBuilder:
    """Generic domain-aware prompt builder for domains without rich templates."""

    def __init__(self, domain_name: str, domain_context: str):
        self.domain_name = domain_name
        self.domain_context = domain_context

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating search prompts for AI assistants in the {self.domain_name} domain.

CONTEXT:
- Business domain: {self.domain_name} ({self.domain_context})
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

YOUR TASK:
For each keyword, generate exactly 1 prompt. Choose the most fitting style:
1. Service/solution finding - Questions about where to find services or solutions
2. Information/comparison - Questions comparing options or seeking detailed information
3. Problem-solving - Questions about solving specific problems or achieving goals

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Natural, conversational questions
   - Direct and to the point
   - Relevant to {self.domain_name} domain

3. DOMAIN CONTEXT: Frame prompts within {self.domain_name}
   - Focus on {self.domain_context}
   - Use domain-specific terminology naturally

4. OUTPUT: Generate exactly 1 prompt per keyword

RESPONSE FORMAT:
Return ONLY valid JSON in this structure:
{{
  "prompts": [
    {{"prompt": "First prompt text...", "source_keyword": "original keyword"}},
    {{"prompt": "Second prompt text...", "source_keyword": "original keyword"}},
    ...
  ]
}}

REMEMBER:
- Exactly 1 prompt per keyword, {len(keywords)} prompts total
- All prompts in {language}
- Short, casual, conversational style
- Stay within {self.domain_name} domain context"""
