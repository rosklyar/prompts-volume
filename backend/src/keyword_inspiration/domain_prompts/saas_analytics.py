"""SaaS analytics domain prompt builder with rich examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class SaasAnalyticsPromptBuilder:
    """Rich analytics/BI software prompt builder."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating analytics and business intelligence software search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (Analytics & BI):

Topic: Product Analytics
- "Best tool for tracking user behavior in an app?"
- "Mixpanel vs Amplitude – which is better?"
- "Simple analytics for a SaaS product?"
- "Tool for funnel analysis and conversion tracking?"

Topic: Business Intelligence
- "Best BI tool for non-technical teams?"
- "Tableau vs Power BI – which to choose?"
- "Dashboard tool that connects to multiple databases?"
- "Affordable BI platform for startups?"

Topic: Data Visualization
- "Best tool for building interactive dashboards?"
- "Analytics platform with real-time data?"
- "How to track KPIs across departments?"
- "Tool for cohort analysis and retention metrics?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and analytics/BI needs
2. Generate exactly 1 SHORT, CASUAL analytics software prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the examples style above
   - Natural, conversational questions
   - Direct and to the point

3. INTENT UNDERSTANDING:

   A) Tool discovery (keywords like "best analytics tool", "top BI platforms"):
      → Create tool recommendation prompts
      → Examples: "Best analytics tool for a mobile app?", "Top BI platform with SQL support?"

   B) Problem-solving (workflow/process questions like "how to track conversions"):
      → Transform to tool-finding prompts
      → Examples: "Which tool is best for conversion tracking?", "Software for automated reporting?"

   C) Comparison (versus/reviews like "Mixpanel vs Amplitude"):
      → Create comparison prompts
      → Examples: "Mixpanel vs Amplitude – which fits early-stage startups?", "Google Analytics alternatives for SaaS?"

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
- Transform indirect intents to analytics tool discovery prompts
- Follow the examples style"""


builder: DomainPromptBuilder = SaasAnalyticsPromptBuilder()
