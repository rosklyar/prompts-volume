"""E-commerce domain prompt builder with rich Ukrainian examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class EcommPromptBuilder:
    """Rich e-commerce prompt builder with intent mapping and examples."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating e-commerce product search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (Ukrainian e-commerce):

Topic: Телевізори
- "Який телевізор краще купити до 10 000 грн?"
- "Телевізор для маленької кімнати – що порадиш?"
- "OLED чи QLED – що вибрати?"
- "Найкращий телевізор для PlayStation 5."

Topic: Смартфони
- "Найкращий смартфон до 15 000 грн."
- "iPhone чи Samsung – що краще у 2025?"
- "Який бюджетний смартфон має хорошу камеру?"
- "Смартфон для ігор до 20 000 грн."

Topic: Побутова техніка
- "Який пилосос купити для квартири?"
- "Робот-пилосос чи звичайний – що краще?"
- "Топ кавоварок для дому."
- "Який блендер обрати для смузі?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and product needs
2. Generate exactly 1 SHORT, CASUAL e-commerce prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the Ukrainian examples style above
   - Natural, conversational questions
   - Direct and to the point
   - Use "–" or "?" for natural breaks

3. INTENT UNDERSTANDING:

   A) DIRECT product searches (keywords like "лучший телефон", "топ ноутбуків"):
      → Create product comparison/recommendation prompts
      → Examples: "Найкращий телефон до 10 000?", "Ноутбук для роботи – що вибрати?"

   B) INDIRECT searches (how-to, tutorials, technical questions):
      → Understand the UNDERLYING PRODUCT NEED
      → Transform to product search prompt

      Examples:
      * Keywords: "як підключити джойстик до телефону", "найкращий телефон для ігор"
        → Prompt: "Який телефон найкращий для ігор з джойстиком?"

      * Keywords: "how to connect bluetooth speaker", "как подключить колонку"
        → Prompt: "Яка блютуз колонка краща до 2000 грн?"

      * Keywords: "печеные яблоки в микроволновке"
        → Prompt: "Яка мікрохвильовка для готування?"

   C) Informational searches (lists, reviews):
      → Create "top/best" or comparison prompts
      → Examples: "Топ-5 смартфонів 2025?", "Які ігри найкращі для телефону?"

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
- Transform indirect intents to product search prompts
- Follow the Ukrainian examples style"""


builder: DomainPromptBuilder = EcommPromptBuilder()
