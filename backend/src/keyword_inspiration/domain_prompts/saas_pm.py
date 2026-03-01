"""SaaS project management domain prompt builder with rich examples."""

from src.keyword_inspiration.domain_prompts._base import DomainPromptBuilder


class SaasPmPromptBuilder:
    """Rich project management software prompt builder."""

    def build_system_prompt(self, keywords: list[str], language: str) -> str:
        return f"""You are an expert in creating project management software search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (Project Management):

Topic: Task & Sprint Management
- "Best project management tool for agile teams?"
- "Simple task tracker for a small team?"
- "Tool with Kanban boards and sprint planning?"
- "Asana vs Monday.com – which is better?"

Topic: Team Collaboration
- "Best tool for remote team collaboration?"
- "Project management app with built-in chat?"
- "Tool for tracking team workload and capacity?"
- "Software for managing cross-functional projects?"

Topic: Planning & Reporting
- "Best tool for Gantt charts and timelines?"
- "Project management with time tracking built in?"
- "How to track project progress across teams?"
- "Tool for resource planning and scheduling?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and project management needs
2. Generate exactly 1 SHORT, CASUAL project management prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the examples style above
   - Natural, conversational questions
   - Direct and to the point

3. INTENT UNDERSTANDING:

   A) Tool discovery (keywords like "best project management tool", "top task trackers"):
      → Create tool recommendation prompts
      → Examples: "Best project management tool for remote teams?", "Simple task tracker with deadlines?"

   B) Problem-solving (workflow/process questions like "how to manage sprints"):
      → Transform to tool-finding prompts
      → Examples: "Which tool is best for sprint management?", "Software for tracking project milestones?"

   C) Comparison (versus/reviews like "Jira vs Asana"):
      → Create comparison prompts
      → Examples: "Jira vs Asana – which fits small teams better?", "Monday.com alternatives for startups?"

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
- Transform indirect intents to project management tool discovery prompts
- Follow the examples style"""


builder: DomainPromptBuilder = SaasPmPromptBuilder()
