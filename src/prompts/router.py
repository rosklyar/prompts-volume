"""Router for prompts generation endpoints."""

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.countries import get_country_by_code
from src.embeddings.clustering_service import ClusteringService
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.embeddings.topic_relevance_filter_service import TopicRelevanceFilterService
from src.prompts.company_meta_info_service import (
    CompanyMetaInfoService,
    get_company_meta_info_service,
)
from src.prompts.data_for_seo_service import DataForSEOService, get_dataforseo_service
from src.prompts.models import GeneratedPrompts
from src.prompts.prompts_generator_service import (
    PromptsGeneratorService,
    get_prompts_generator_service,
)
from src.utils.keyword_filters import (
    deduplicate_keywords,
    filter_by_brand_exclusion,
    filter_by_word_count,
)
from src.utils.url_validator import extract_domain, validate_url

router = APIRouter(prefix="/prompts/api/v1", tags=["prompts"])


@router.get("/generate", response_model=GeneratedPrompts)
async def generate_prompts(
    company_url: str = Query(
        ..., description="Company website URL (e.g., 'moyo.ua', 'https://example.com')"
    ),
    iso_country_code: str = Query(
        ..., description="ISO 3166-1 alpha-2 country code (e.g., 'UA', 'US')"
    ),
    dataforseo_service: DataForSEOService = Depends(get_dataforseo_service),
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
    meta_service: CompanyMetaInfoService = Depends(get_company_meta_info_service),
    prompts_service: PromptsGeneratorService = Depends(get_prompts_generator_service),
):
    """
    Generate e-commerce product search prompts from company URL and country.

    Complete automated pipeline:
    1. Validate URL and extract domain
    2. Get country info (location, language)
    3. Fetch ALL keywords from DataForSEO (paginated, up to 10k)
    4. Get company metadata (topics, brand variations)
    5. Filter keywords (word count ≥3, brand exclusion, dedupe)
    6. Generate embeddings for keywords
    7. Cluster keywords with HDBSCAN
    8. Filter clusters by topic relevance
    9. Generate e-commerce prompts (5 keywords per prompt)

    Args:
        company_url: Company website URL
        iso_country_code: ISO country code for targeting

    Returns:
        GeneratedPrompts with topics, clusters, and their prompts

    Raises:
        HTTPException 400: Invalid URL or ISO code
        HTTPException 404: No keywords found
        HTTPException 500: Pipeline errors

    Example:
        GET /prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA
    """
    try:
        # 1. Validate URL and extract domain
        await validate_url(company_url)
        domain = extract_domain(company_url)

        # 2. Get country info
        country = get_country_by_code(iso_country_code)
        if not country:
            raise HTTPException(
                status_code=400, detail=f"Invalid ISO country code: {iso_country_code}"
            )

        location_name = country.name
        language = (
            country.preferred_languages[0].name
            if country.preferred_languages
            else "English"
        )

        # 3. Fetch ALL keywords with pagination
        keywords = await dataforseo_service.get_all_keywords_for_site(
            target_domain=domain,
            location_name=location_name,
            language=language,
            batch_size=1000,
            max_total=10000,
        )

        if not keywords:
            raise HTTPException(
                status_code=404, detail=f"No keywords found for domain: {domain}"
            )

        # 4. Get company metadata (topics, brand variations)
        meta_info = meta_service.get_meta_info(domain)

        # 5. Filter keywords
        filtered_keywords = filter_by_word_count(keywords, min_words=3)
        filtered_keywords = filter_by_brand_exclusion(
            filtered_keywords, meta_info.brand_variations
        )
        filtered_keywords = deduplicate_keywords(filtered_keywords)

        if not filtered_keywords:
            raise HTTPException(
                status_code=404, detail="No keywords remaining after filtering"
            )

        # 6. Generate embeddings
        keyword_embeddings = embeddings_service.encode_keywords(
            filtered_keywords, batch_size=64
        )

        # 7. Cluster with HDBSCAN
        clustering_service = ClusteringService()
        embeddings_array = np.array([ke.embedding for ke in keyword_embeddings])

        clustering_result = clustering_service.cluster(
            keywords=filtered_keywords,
            embeddings=embeddings_array,
            min_cluster_size=5,
            min_samples=5,
            cluster_selection_epsilon=0.0,
        )

        # 8. Filter clusters by topic relevance
        topic_filter = TopicRelevanceFilterService(embeddings_service)
        filtered_by_topic = topic_filter.filter_by_topics(
            clustering_result=clustering_result,
            topics=meta_info.topics,
            similarity_threshold=0.7,
            min_relevant_ratio=0.5,
        )

        # 9. Remove empty topics and generate prompts
        topics_with_clusters = {
            topic: clusters for topic, clusters in filtered_by_topic.items() if clusters
        }

        if not topics_with_clusters:
            raise HTTPException(
                status_code=404, detail="No relevant topic clusters found"
            )

        result = await prompts_service.generate_prompts(
            topics_with_clusters=topics_with_clusters, number_of_keywords_for_prompt=5
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate prompts: {str(e)}"
        )
