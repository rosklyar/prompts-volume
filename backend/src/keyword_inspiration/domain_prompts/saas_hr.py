"""SaaS HR domain prompt builder with rich examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class SaasHrPromptBuilder:
    """Rich HR/people management software prompt builder."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating HR and people management software search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (HR & People):

Topic: Payroll & Benefits
- "Best payroll software for a small company?"
- "Gusto vs Rippling – which is simpler?"
- "Tool for managing employee benefits?"
- "Payroll platform that handles multi-state taxes?"

Topic: Hiring & Onboarding
- "Best applicant tracking system for startups?"
- "Tool for automating employee onboarding?"
- "ATS with built-in interview scheduling?"
- "Software for managing remote hiring?"

Topic: Performance & Engagement
- "Best tool for employee performance reviews?"
- "Software for tracking OKRs and goals?"
- "How to run employee engagement surveys?"
- "BambooHR vs Rippling – which is better for HR?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and HR/people management needs
2. Generate exactly 1 SHORT, CASUAL HR software prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the examples style above
   - Natural, conversational questions
   - Direct and to the point

3. INTENT UNDERSTANDING:

   A) Tool discovery (keywords like "best HR software", "top payroll tools"):
      → Create tool recommendation prompts
      → Examples: "Best HR software for a 50-person company?", "Top payroll tool with benefits admin?"

   B) Problem-solving (workflow/process questions like "how to onboard employees"):
      → Transform to tool-finding prompts
      → Examples: "Which tool is best for employee onboarding?", "Software for tracking time off and PTO?"

   C) Comparison (versus/reviews like "BambooHR vs Gusto"):
      → Create comparison prompts
      → Examples: "BambooHR vs Gusto – which is better for small teams?", "Rippling alternatives for HR and payroll?"

RESPONSE FORMAT:
Return ONLY valid JSON in this structure:
{{
  "prompts": [
    {{"prompt": "Short casual prompt...", "source_keyword": "original keyword"}},
    ...
  ]
}}

REMEMBER:
- Exactly 1 prompt per keyword, {len(keywords)} prompts total
- All prompts in {language}
- Short (5-15 words), casual, conversational
- Transform indirect intents to HR tool discovery prompts
- Follow the examples style"""


builder: DomainPromptBuilder = SaasHrPromptBuilder()
