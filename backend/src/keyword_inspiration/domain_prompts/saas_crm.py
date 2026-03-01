"""SaaS CRM domain prompt builder with rich examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class SaasCrmPromptBuilder:
    """Rich CRM/sales software prompt builder."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating CRM and sales software search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (CRM & Sales):

Topic: Contact Management
- "Best CRM for managing 10,000+ contacts?"
- "CRM with automatic contact enrichment?"
- "Which CRM has the best email integration?"
- "Simple CRM for a small sales team?"

Topic: Sales Pipeline
- "Best tool for tracking sales deals?"
- "CRM with visual pipeline management?"
- "How to automate follow-up emails in a CRM?"
- "CRM for B2B sales with forecasting?"

Topic: Customer Communication
- "CRM with built-in calling and texting?"
- "Best CRM for managing client relationships?"
- "HubSpot vs Salesforce for small business?"
- "CRM that integrates with WhatsApp?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and CRM/sales needs
2. Generate exactly 1 SHORT, CASUAL CRM software prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the examples style above
   - Natural, conversational questions
   - Direct and to the point

3. INTENT UNDERSTANDING:

   A) Tool discovery (keywords like "best CRM", "top sales tools"):
      → Create tool recommendation prompts
      → Examples: "Best CRM for a 10-person sales team?", "Top CRM with email tracking?"

   B) Problem-solving (workflow/process questions like "how to track leads"):
      → Transform to tool-finding prompts
      → Examples: "Which CRM is best for lead tracking?", "Tool for automating sales outreach?"

   C) Comparison (versus/reviews like "HubSpot vs Pipedrive"):
      → Create comparison prompts
      → Examples: "HubSpot vs Pipedrive – which is better for startups?", "Salesforce alternatives for small teams?"

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
- Transform indirect intents to CRM/sales tool discovery prompts
- Follow the examples style"""


builder: DomainPromptBuilder = SaasCrmPromptBuilder()
