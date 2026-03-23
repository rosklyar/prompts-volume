"""Static reference data for GEO schema audit."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RichResultType:
    schema_type: str
    required_properties: tuple[str, ...]
    recommended_properties: tuple[str, ...] = ()


GOOGLE_RICH_RESULT_TYPES: dict[str, RichResultType] = {
    "Article": RichResultType(
        schema_type="Article",
        required_properties=("headline", "image", "datePublished", "author"),
        recommended_properties=("dateModified", "mainEntityOfPage"),
    ),
    "NewsArticle": RichResultType(
        schema_type="NewsArticle",
        required_properties=("headline", "image", "datePublished", "author"),
        recommended_properties=("dateModified", "mainEntityOfPage"),
    ),
    "BlogPosting": RichResultType(
        schema_type="BlogPosting",
        required_properties=("headline", "image", "datePublished", "author"),
        recommended_properties=("dateModified", "mainEntityOfPage"),
    ),
    "BreadcrumbList": RichResultType(
        schema_type="BreadcrumbList",
        required_properties=("itemListElement",),
    ),
    "FAQPage": RichResultType(
        schema_type="FAQPage",
        required_properties=("mainEntity",),
    ),
    "HowTo": RichResultType(
        schema_type="HowTo",
        required_properties=("name", "step"),
    ),
    "LocalBusiness": RichResultType(
        schema_type="LocalBusiness",
        required_properties=("name", "address"),
        recommended_properties=("telephone", "openingHoursSpecification", "geo"),
    ),
    "Organization": RichResultType(
        schema_type="Organization",
        required_properties=("name", "url"),
        recommended_properties=("logo", "sameAs", "description", "contactPoint"),
    ),
    "Person": RichResultType(
        schema_type="Person",
        required_properties=("name",),
        recommended_properties=("url", "sameAs", "jobTitle", "image"),
    ),
    "Product": RichResultType(
        schema_type="Product",
        required_properties=("name", "image", "offers"),
        recommended_properties=("description", "brand", "review", "aggregateRating"),
    ),
    "Review": RichResultType(
        schema_type="Review",
        required_properties=("itemReviewed", "reviewRating", "author"),
    ),
    "WebSite": RichResultType(
        schema_type="WebSite",
        required_properties=("url", "name"),
        recommended_properties=("potentialAction",),
    ),
    "VideoObject": RichResultType(
        schema_type="VideoObject",
        required_properties=("name", "description", "thumbnailUrl", "uploadDate"),
    ),
    "Event": RichResultType(
        schema_type="Event",
        required_properties=("name", "startDate", "location"),
        recommended_properties=("eventAttendanceMode", "eventStatus"),
    ),
    "Recipe": RichResultType(
        schema_type="Recipe",
        required_properties=("name", "image"),
        recommended_properties=(
            "author", "datePublished", "prepTime", "cookTime", "recipeIngredient",
        ),
    ),
    "Course": RichResultType(
        schema_type="Course",
        required_properties=("name", "description", "provider"),
    ),
    "SoftwareApplication": RichResultType(
        schema_type="SoftwareApplication",
        required_properties=("name", "offers"),
        recommended_properties=("applicationCategory", "operatingSystem"),
    ),
}

# Schema types that are subtypes of Article for matching purposes
ARTICLE_SUBTYPES = {"Article", "NewsArticle", "BlogPosting", "TechArticle", "ScholarlyArticle"}

# Schema types that are subtypes of Organization
ORGANIZATION_SUBTYPES = {
    "Organization", "LocalBusiness", "Corporation", "EducationalOrganization",
    "GovernmentOrganization", "MedicalOrganization", "NGO", "PerformingGroup",
    "SportsOrganization", "Airline", "Consortium", "FundingScheme",
    "NewsMediaOrganization", "OnlineBusiness", "Project", "ResearchOrganization",
    "WorkersUnion",
}


@dataclass(frozen=True)
class DeprecatedSchemaInfo:
    schema_type: str
    status: str  # "removed" | "restricted" | "deprecated"
    message: str


DEPRECATED_SCHEMAS: dict[str, DeprecatedSchemaInfo] = {
    "HowTo": DeprecatedSchemaInfo(
        schema_type="HowTo",
        status="removed",
        message="HowTo rich results removed by Google in September 2023. "
                "Schema provides no search benefit. Consider removing.",
    ),
    "FAQPage": DeprecatedSchemaInfo(
        schema_type="FAQPage",
        status="restricted",
        message="FAQPage rich results restricted to government and health authority "
                "sites since August 2023. May still help AI models understand Q&A structure.",
    ),
    "SpecialAnnouncement": DeprecatedSchemaInfo(
        schema_type="SpecialAnnouncement",
        status="deprecated",
        message="SpecialAnnouncement (COVID-19) is deprecated. No longer actively supported.",
    ),
    "CourseInfo": DeprecatedSchemaInfo(
        schema_type="CourseInfo",
        status="deprecated",
        message="CourseInfo is deprecated. Replaced by updated Course schema structure.",
    ),
}


@dataclass(frozen=True)
class ScoringComponent:
    name: str
    max_points: float
    description: str


SCORING_COMPONENTS: list[ScoringComponent] = [
    ScoringComponent("organization", 20, "Organization/LocalBusiness with sameAs"),
    ScoringComponent("article", 15, "Article/content schema with author and dateModified"),
    ScoringComponent("person", 15, "Person schema for author with sameAs and expertise"),
    ScoringComponent("same_as", 15, "sameAs cross-platform entity linking completeness"),
    ScoringComponent("speakable", 10, "speakable property for AI assistant readiness"),
    ScoringComponent("breadcrumb", 5, "BreadcrumbList for navigation context"),
    ScoringComponent("website_search_action", 5, "WebSite + SearchAction for sitelinks"),
    ScoringComponent("no_deprecated", 5, "No deprecated/removed schemas present"),
    ScoringComponent("json_ld_format", 5, "All schemas in JSON-LD format"),
    ScoringComponent("validation", 5, "All schemas pass syntax and property validation"),
]

# Platforms checked for sameAs entity linking
SAME_AS_PLATFORMS: dict[str, str] = {
    "wikipedia": "wikipedia.org",
    "wikidata": "wikidata.org",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "crunchbase": "crunchbase.com",
    "twitter": "twitter.com",
    "x": "x.com",
    "facebook": "facebook.com",
    "github": "github.com",
}
