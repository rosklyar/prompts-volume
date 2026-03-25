"""Integration test for keyword inspiration endpoints.

Only mocks the external DataForSEO API. Embeddings (sentence-transformers)
and clustering (HDBSCAN) run for real.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import settings
from src.database.models import KeywordCache
from src.keyword_inspiration.services.data_for_seo_service import (
    DataForSEOPaymentError,
    RankedKeywordData,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLUSTERS_SNAPSHOT = FIXTURES_DIR / "discovered_clusters.json"


def _delete_cache(engine, domains: list[str]) -> None:
    """Delete KeywordCache rows for the given domains so the API-fetch path is exercised."""
    from sqlalchemy import delete

    async def _remove():
        session_maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as session:
            await session.execute(
                delete(KeywordCache).where(KeywordCache.domain.in_(domains))
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_remove())


def _set_keyword_filter_config(engine, domain_id: int, config: list[dict]) -> None:
    """Set keyword_filter_config on a business domain."""
    from sqlalchemy import text

    async def _update():
        session_maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as session:
            await session.execute(
                text(
                    "UPDATE business_domains SET keyword_filter_config = :config WHERE id = :id"
                ),
                {"config": json.dumps(config), "id": domain_id},
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_update())


def test_discover_clusters(client, test_engine, auth_headers):
    """Integration: discover-clusters with 2 API-fetched + 2 cached domains.

    Verifies:
    - DataForSEO called only for uncached domains (moyo.ua, ctrs.com.ua)
    - Cached domains (allo.ua, eldorado.ua) skip the API
    - Response contains scored clusters with expected fields
    - No brand keywords leak into clusters
    """
    # -- Load fixture --
    with open(FIXTURES_DIR / "dataforseo_keywords.json") as f:
        fixture = json.load(f)

    moyo_raw = fixture[0:1000]
    ctrs_raw = fixture[1000:2000]

    # -- Delete seed cache for moyo.ua and ctrs.com.ua to exercise API-fetch path --
    # (allo.ua and eldorado.ua remain cached from seed_initial_data)
    _delete_cache(test_engine, ["moyo.ua", "ctrs.com.ua"])

    # -- Set brand_exclusion filter on e-comm business domain (id=1) --
    _set_keyword_filter_config(test_engine, 1, [{"type": "word_count", "operator": "gte", "value": 2}, {"type": "brand_exclusion"}])

    # -- Build mock DataForSEO responses --
    def _to_ranked(entries: list[dict]) -> list[RankedKeywordData]:
        return [
            RankedKeywordData(
                keyword=e["keyword"],
                search_volume=e["search_volume"],
                rank_group=e["rank_group"],
            )
            for e in entries
        ]

    moyo_ranked = _to_ranked(moyo_raw)
    ctrs_ranked = _to_ranked(ctrs_raw)

    async def _mock_fetch(*, target_domain: str, **_kwargs) -> list[RankedKeywordData]:
        if target_domain == "moyo.ua":
            return moyo_ranked
        if target_domain == "ctrs.com.ua":
            return ctrs_ranked
        raise ValueError(f"Unexpected domain: {target_domain}")

    # -- Mock only DataForSEO --
    with patch(
        "src.keyword_inspiration.services.data_for_seo_service"
        ".DataForSEOService.get_all_ranked_keywords_for_site",
        new_callable=AsyncMock,
        side_effect=_mock_fetch,
    ) as mock_fetch:
        resp = client.post(
            "/keyword-inspiration/api/v1/discover-clusters",
            json={
                "domains": ["moyo.ua", "ctrs.com.ua", "allo.ua", "eldorado.ua"],
                "country_code": "UA",
                "language_name": "Ukrainian",
                "brand_names": ["moyo", "мойо"],
                "business_domain_id": 1,
            },
            headers=auth_headers,
        )

    # -- Assertions --
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # DataForSEO called exactly twice (moyo.ua + ctrs.com.ua)
    assert mock_fetch.call_count == 2
    called_domains = {
        call.kwargs["target_domain"] for call in mock_fetch.call_args_list
    }
    assert called_domains == {"moyo.ua", "ctrs.com.ua"}

    # Clusters present
    clusters = data["clusters"]
    assert len(clusters) > 0

    # Each cluster has required fields
    for cluster in clusters:
        assert isinstance(cluster["cluster_id"], int)
        assert len(cluster["keywords"]) > 0
        assert isinstance(cluster["score"], (int, float))
        assert isinstance(cluster["title"], str)
        assert cluster["keyword_count"] > 0

    # Total keywords populated
    assert data["total_keywords"] > 0

    # No brand keywords in any cluster
    brand_names_lower = {"moyo", "мойо"}
    for cluster in clusters:
        for kw in cluster["keywords"]:
            kw_lower = kw.lower()
            for brand in brand_names_lower:
                assert brand not in kw_lower, (
                    f"Brand '{brand}' found in keyword '{kw}'"
                )

    # Save top 3 clusters to fixture file for generate-prompts test
    snapshot = clusters[:3]
    CLUSTERS_SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))


def test_discover_clusters_skips_402_domains(client, test_engine, auth_headers):
    """When DataForSEO returns 402 for uncached domains, they are skipped gracefully.

    Cached domains (allo.ua, eldorado.ua) still contribute data, so the endpoint
    returns clusters from cached data only — no 500 error.
    """
    _delete_cache(test_engine, ["moyo.ua", "ctrs.com.ua"])

    async def _mock_fetch(*, target_domain: str, **_kwargs) -> list[RankedKeywordData]:
        raise DataForSEOPaymentError("No credits")

    with patch(
        "src.keyword_inspiration.services.data_for_seo_service"
        ".DataForSEOService.get_all_ranked_keywords_for_site",
        new_callable=AsyncMock,
        side_effect=_mock_fetch,
    ):
        resp = client.post(
            "/keyword-inspiration/api/v1/discover-clusters",
            json={
                "domains": ["moyo.ua", "ctrs.com.ua", "allo.ua", "eldorado.ua"],
                "country_code": "UA",
                "language_name": "Ukrainian",
                "brand_names": ["moyo", "мойо"],
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Clusters from cached domains should still be present
    assert data["total_keywords"] > 0
    assert len(data["clusters"]) > 0


@pytest.mark.skipif(not settings.openai_api_key, reason="OPENAI_API_KEY required")
def test_generate_prompts(client, auth_headers):
    """Integration: generate prompts from discovered clusters using real OpenAI.

    Reads clusters from the snapshot file saved by test_discover_clusters.
    Run test_discover_clusters first to create the snapshot.
    """
    if not CLUSTERS_SNAPSHOT.exists():
        pytest.skip(f"No cluster snapshot at {CLUSTERS_SNAPSHOT} — run test_discover_clusters first")

    clusters = json.loads(CLUSTERS_SNAPSHOT.read_text())
    first_cluster = clusters[0]
    second_cluster = clusters[1]
    third_cluster = clusters[2]

    resp = client.post(
        "/keyword-inspiration/api/v1/generate-prompts",
        json={
            "clusters": [
                {
                    "cluster_id": first_cluster["cluster_id"],
                    "title": first_cluster["title"],
                    "keywords": first_cluster["keywords"],
                },
                {
                    "cluster_id": second_cluster["cluster_id"],
                    "title": second_cluster["title"],
                    "keywords": second_cluster["keywords"],
                },
                {
                    "cluster_id": third_cluster["cluster_id"],
                    "title": third_cluster["title"],
                    "keywords": third_cluster["keywords"],
                }
            ],
            "business_domain_id": 1,
            "language": "Ukrainian",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "clusters" in data
    assert len(data["clusters"]) == 3
    assert data["total_prompts"] > 0
    for cluster in data["clusters"]:
        assert "cluster_id" in cluster
        assert "title" in cluster
        assert "prompts" in cluster
        for prompt in cluster["prompts"]:
            assert "prompt_text" in prompt
            assert isinstance(prompt["prompt_text"], str)
            assert len(prompt["prompt_text"]) > 0
