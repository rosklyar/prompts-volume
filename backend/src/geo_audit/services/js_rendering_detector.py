"""Service for detecting JS framework signatures in HTML."""

import re

from src.geo_audit.models.domain_models import JsRenderingWarning

_AI_CRAWLER_NOTE = (
    "AI crawlers (GPTBot, ClaudeBot, PerplexityBot) generally do NOT execute "
    "JavaScript and will miss JS-injected schemas entirely."
)

_FRAMEWORK_SIGNATURES: list[tuple[str, str, str, str]] = [
    # (framework, pattern, confidence, detail)
    ("Next.js", r'__NEXT_DATA__', "high",
     "Next.js detected. Schemas may be server-rendered (good) or client-rendered."),
    ("Next.js", r'id="__next"', "medium",
     "Next.js root element detected."),
    ("Nuxt.js", r'__NUXT__', "high",
     "Nuxt.js detected. Check if schemas are in SSR output."),
    ("React", r'data-reactroot', "high",
     "React app detected. Schemas injected after hydration are invisible to AI crawlers."),
    ("React", r'_reactRootContainer', "high",
     "React root container detected."),
    ("Vue.js", r'id="app"[^>]*data-v-', "medium",
     "Vue.js app detected. Check if schemas are server-rendered."),
    ("Angular", r'ng-version=', "high",
     "Angular detected. Schemas are likely client-rendered and invisible to AI crawlers."),
    ("Angular", r'ng-app', "medium",
     "AngularJS detected."),
    ("Gatsby", r'___gatsby', "high",
     "Gatsby detected. Static site generation typically includes schemas in HTML."),
    ("SPA", r'window\.__INITIAL_STATE__', "medium",
     "SPA state hydration detected. Schemas may be injected after initial load."),
]


class JsRenderingDetector:
    """Detects JS framework signatures that may affect schema visibility."""

    def detect(self, html: str) -> list[JsRenderingWarning]:
        warnings: list[JsRenderingWarning] = []
        seen_frameworks: set[str] = set()

        for framework, pattern, confidence, detail in _FRAMEWORK_SIGNATURES:
            if framework in seen_frameworks:
                continue
            if re.search(pattern, html):
                seen_frameworks.add(framework)
                warnings.append(JsRenderingWarning(
                    framework=framework,
                    confidence=confidence,
                    message=f"{detail} {_AI_CRAWLER_NOTE}",
                ))

        return warnings
