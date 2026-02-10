"""Prompt templates for competitor discovery."""

COMPETITOR_SEARCH_PROMPT = """You are a market research analyst. Your task is to identify the main competitors of {brand_name} ({target_domain}) in {country}.

INSTRUCTIONS:
1. Use web search to find the top {num_competitors} direct competitors of {brand_name}
2. Focus on companies operating in the same market/industry
3. Prioritize competitors that are well-known in {country}
4. Exclude {brand_name_lower} and its subsidiaries
5. Include only actual competing brands, not parent companies or holding groups

RESPONSE FORMAT:
Return ONLY valid JSON array with competitor objects:
[
  {{"name": "Competitor Name", "domain": "competitor.com"}},
  {{"name": "Another Competitor", "domain": "another.com"}}
]

If a domain is unknown, use null for the domain field.
Do not include any explanation or markdown, just the JSON array.
"""
