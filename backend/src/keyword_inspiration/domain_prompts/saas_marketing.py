"""SaaS marketing automation domain prompt builder with rich examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class SaasMarketingPromptBuilder:
    """Rich marketing automation software prompt builder."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating marketing automation software search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (Marketing Automation):

Topic: Email Marketing
- "Best email marketing tool for small business?"
- "Mailchimp vs SendGrid – which is cheaper?"
- "Tool for automated email drip campaigns?"
- "Email platform with best deliverability rates?"

Topic: Campaign Management
- "Best tool for multi-channel marketing campaigns?"
- "Marketing automation for lead nurturing?"
- "Software for A/B testing email campaigns?"
- "All-in-one marketing platform for startups?"

Topic: Lead Generation
- "Best tool for landing pages and lead capture?"
- "Marketing software with built-in CRM?"
- "How to automate lead scoring?"
- "ActiveCampaign vs HubSpot for email automation?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and marketing automation needs
2. Generate exactly 1 SHORT, CASUAL marketing software prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the examples style above
   - Natural, conversational questions
   - Direct and to the point

3. INTENT UNDERSTANDING:

   A) Tool discovery (keywords like "best email tool", "top marketing platforms"):
      → Create tool recommendation prompts
      → Examples: "Best email marketing tool under $50/month?", "Top marketing automation for e-commerce?"

   B) Problem-solving (workflow/process questions like "how to nurture leads"):
      → Transform to tool-finding prompts
      → Examples: "Which tool is best for lead nurturing?", "Software for automating social media posts?"

   C) Comparison (versus/reviews like "Mailchimp vs ActiveCampaign"):
      → Create comparison prompts
      → Examples: "Mailchimp vs ActiveCampaign – which is better for automation?", "SendGrid alternatives for transactional email?"

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
- Transform indirect intents to marketing tool discovery prompts
- Follow the examples style"""


builder: DomainPromptBuilder = SaasMarketingPromptBuilder()
