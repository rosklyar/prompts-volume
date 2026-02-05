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

BATCH_VARIATION_GENERATION_PROMPT = """Generate UP TO 3 brand name variations for EACH of the following brands in these languages: {languages}.

BRANDS TO PROCESS:
{brands_list}

CRITICAL REQUIREMENTS:
- ALL variations MUST be lowercase (e.g., "найк" not "Найк", "mcdonalds" not "McDonalds")
- Generate ONLY variations that REAL PEOPLE actually use when searching for this brand
- Include ONLY high-confidence variations you are CERTAIN people use
- It is better to return fewer variations than to include uncertain ones
- Do NOT include language labels, parentheses, or explanations
- Do NOT include the original brand name as a variation
- Do NOT include variations that are just the root word with a suffix

WHAT QUALIFIES AS A VALID VARIATION:
1. Common misspellings that real searchers make
2. Transliterations for non-Latin scripts that are widely used (Cyrillic, Chinese, Arabic, etc.)
3. Abbreviated or shortened forms that are commonly recognized

RESPONSE FORMAT:
Return ONLY valid JSON object mapping brand names to their variations array:
{{
  "Brand1": ["variation1", "variation2"],
  "Brand2": ["variation1"],
  "Brand3": []
}}

Do not include any explanation or markdown, just the JSON object.
"""

VARIATION_GENERATION_PROMPT = """Generate UP TO 3 brand name variations for "{brand_name}" in these languages: {languages}.

CRITICAL REQUIREMENTS:
- ALL variations MUST be lowercase (e.g., "найк" not "Найк", "mcdonalds" not "McDonalds")
- Generate ONLY variations that REAL PEOPLE actually use when searching for this brand
- Include ONLY high-confidence variations you are CERTAIN people use
- It is better to return fewer variations than to include uncertain ones
- Do NOT include language labels, parentheses, or explanations
- Do NOT include the original brand name as a variation
- Do NOT include variations that are just the root word with a suffix (e.g., if "nike" is a variation, do NOT also include "nikes")

WHAT QUALIFIES AS A VALID VARIATION:
1. Common misspellings that real searchers make (e.g., "макдоналдз" instead of "макдональдс")
2. Transliterations for non-Latin scripts that are widely used (Cyrillic, Chinese, Arabic, etc.)
3. Abbreviated or shortened forms that are commonly recognized (e.g., "mcd" for McDonald's)

WHAT TO EXCLUDE:
- Any uppercase letters - all output must be lowercase
- Variations that only add a suffix to another variation (avoid "nike" + "nikes", keep only "nike")
- Random transliterations that nobody uses
- Invented abbreviations
- Variations you're not confident about
- The exact original brand name

EXAMPLES:
Brand: "Nike", Languages: English, Russian
Variations: ["найк"]

Brand: "McDonald's", Languages: English, Ukrainian
Variations: ["mcdonalds", "макдональдс", "макдоналдз"]

Brand: "Apple", Languages: English, Japanese
Variations: ["アップル"]

RESPONSE FORMAT:
Return ONLY a valid JSON array with 1-3 lowercase strings (or empty array if no confident variations):
["variation1", "variation2"]

Do not include any explanation or markdown, just the JSON array.
"""
