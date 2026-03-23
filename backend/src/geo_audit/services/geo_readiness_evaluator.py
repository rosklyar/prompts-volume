"""Service for evaluating GEO-critical schema completeness."""

from src.geo_audit.constants import ARTICLE_SUBTYPES, ORGANIZATION_SUBTYPES, SAME_AS_PLATFORMS
from src.geo_audit.models.domain_models import DetectedSchema, GeoReadinessResult, GeoSignal, SameAsLink


class GeoReadinessEvaluator:
    """Evaluates presence and completeness of GEO-critical schemas."""

    def evaluate(self, schemas: list[DetectedSchema]) -> GeoReadinessResult:
        signals: list[GeoSignal] = [
            self._check_organization(schemas),
            self._check_person(schemas),
            self._check_article(schemas),
            self._check_speakable(schemas),
            self._check_website_search_action(schemas),
        ]
        same_as_links = self._extract_same_as_links(schemas)

        present_count = sum(1 for s in signals if s.present)
        overall = present_count / len(signals) if signals else 0.0

        return GeoReadinessResult(
            signals=signals,
            same_as_links=same_as_links,
            overall_readiness=overall,
        )

    def _find_by_types(
        self, schemas: list[DetectedSchema], type_set: set[str],
    ) -> list[DetectedSchema]:
        return [s for s in schemas if s.schema_type in type_set]

    def _check_organization(self, schemas: list[DetectedSchema]) -> GeoSignal:
        orgs = self._find_by_types(schemas, ORGANIZATION_SUBTYPES)
        if not orgs:
            return GeoSignal(
                name="Organization",
                present=False,
                completeness=0.0,
                details="No Organization or LocalBusiness schema found",
            )

        org = orgs[0]
        props = org.properties
        key_fields = ["name", "url", "logo", "description", "sameAs", "contactPoint", "address", "foundingDate"]
        present = sum(1 for f in key_fields if f in props)
        completeness = present / len(key_fields)

        same_as = props.get("sameAs", [])
        if isinstance(same_as, str):
            same_as = [same_as]
        same_as_count = len(same_as) if isinstance(same_as, list) else 0

        details_parts = [f"{present}/{len(key_fields)} key properties present"]
        if same_as_count:
            details_parts.append(f"sameAs links to {same_as_count} platform(s)")
        else:
            details_parts.append("MISSING sameAs — critical for GEO entity linking")

        return GeoSignal(
            name="Organization",
            present=True,
            completeness=completeness,
            details=". ".join(details_parts),
        )

    def _check_person(self, schemas: list[DetectedSchema]) -> GeoSignal:
        persons = [s for s in schemas if s.schema_type == "Person"]
        if not persons:
            return GeoSignal(
                name="Person",
                present=False,
                completeness=0.0,
                details="No Person schema found for author identity",
            )

        person = persons[0]
        props = person.properties
        key_fields = ["name", "url", "sameAs", "jobTitle", "worksFor", "image", "description", "knowsAbout"]
        present = sum(1 for f in key_fields if f in props)
        completeness = present / len(key_fields)

        return GeoSignal(
            name="Person",
            present=True,
            completeness=completeness,
            details=f"{present}/{len(key_fields)} key properties present for author E-E-A-T signals",
        )

    def _check_article(self, schemas: list[DetectedSchema]) -> GeoSignal:
        articles = self._find_by_types(schemas, ARTICLE_SUBTYPES)
        if not articles:
            return GeoSignal(
                name="Article",
                present=False,
                completeness=0.0,
                details="No Article/BlogPosting/NewsArticle schema found",
            )

        article = articles[0]
        props = article.properties
        key_fields = [
            "headline", "author", "datePublished", "dateModified",
            "publisher", "image", "description", "mainEntityOfPage",
        ]
        present = sum(1 for f in key_fields if f in props)
        completeness = present / len(key_fields)

        author = props.get("author")
        author_is_person = isinstance(author, dict) and author.get("@type") == "Person"
        has_date_modified = "dateModified" in props

        details_parts = [f"{present}/{len(key_fields)} key properties"]
        if not author_is_person:
            details_parts.append("author should be a Person object")
        if not has_date_modified:
            details_parts.append("missing dateModified")

        return GeoSignal(
            name="Article",
            present=True,
            completeness=completeness,
            details=". ".join(details_parts),
        )

    def _check_speakable(self, schemas: list[DetectedSchema]) -> GeoSignal:
        for schema in schemas:
            speakable = schema.properties.get("speakable")
            if speakable:
                has_selector = False
                if isinstance(speakable, dict):
                    has_selector = bool(
                        speakable.get("cssSelector") or speakable.get("xpath")
                    )
                elif isinstance(speakable, list):
                    has_selector = any(
                        isinstance(s, dict) and (s.get("cssSelector") or s.get("xpath"))
                        for s in speakable
                    )

                return GeoSignal(
                    name="speakable",
                    present=True,
                    completeness=1.0 if has_selector else 0.5,
                    details="speakable property found"
                    + (" with CSS/XPath selectors" if has_selector else " but missing cssSelector/xpath"),
                )

        return GeoSignal(
            name="speakable",
            present=False,
            completeness=0.0,
            details="No speakable property found — add to signal AI assistant readiness",
        )

    def _check_website_search_action(self, schemas: list[DetectedSchema]) -> GeoSignal:
        websites = [s for s in schemas if s.schema_type == "WebSite"]
        if not websites:
            return GeoSignal(
                name="WebSite+SearchAction",
                present=False,
                completeness=0.0,
                details="No WebSite schema found",
            )

        website = websites[0]
        props = website.properties
        potential_action = props.get("potentialAction")

        if not potential_action:
            return GeoSignal(
                name="WebSite+SearchAction",
                present=True,
                completeness=0.3,
                details="WebSite found but missing potentialAction with SearchAction",
            )

        # Check if SearchAction is properly configured
        actions = potential_action if isinstance(potential_action, list) else [potential_action]
        has_search = any(
            isinstance(a, dict) and a.get("@type") == "SearchAction"
            for a in actions
        )

        if has_search:
            return GeoSignal(
                name="WebSite+SearchAction",
                present=True,
                completeness=1.0,
                details="WebSite with SearchAction properly configured",
            )

        return GeoSignal(
            name="WebSite+SearchAction",
            present=True,
            completeness=0.5,
            details="WebSite found with potentialAction but no SearchAction type",
        )

    def _extract_same_as_links(self, schemas: list[DetectedSchema]) -> list[SameAsLink]:
        """Extract sameAs links from Organization and Person schemas."""
        all_same_as: list[str] = []
        for schema in schemas:
            same_as = schema.properties.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if isinstance(same_as, list):
                all_same_as.extend(str(u) for u in same_as if isinstance(u, str))

        links: list[SameAsLink] = []
        for platform, domain in SAME_AS_PLATFORMS.items():
            matching = [u for u in all_same_as if domain in u]
            if matching:
                links.append(SameAsLink(platform=platform, linked=True, url=matching[0]))
            else:
                links.append(SameAsLink(platform=platform, linked=False))

        return links
