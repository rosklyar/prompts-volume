"""API router for Bright Data webhook endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.brightdata.deps import WebhookAuthDep
from src.brightdata.models.api_models import (
    AllBatchesResponse,
    BatchResponse,
    BrightDataWebhookItem,
    CitationResponse,
    ResultResponse,
    WebhookResponse,
)
from src.brightdata.models.domain import BatchStatus, ParsedCitation, ParsedResult
from src.brightdata.services.batch_registry import (
    InMemoryBatchRegistry,
    get_batch_registry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations/api/v1", tags=["brightdata"])


@router.post("/webhook/{batch_id}", response_model=WebhookResponse)
async def receive_brightdata_webhook(
    batch_id: str,
    request: Request,
    _auth: WebhookAuthDep,
    registry: InMemoryBatchRegistry = Depends(get_batch_registry),
) -> WebhookResponse:
    """
    Receive webhook from Bright Data with scraping results.

    This endpoint is called by Bright Data when scraping completes.
    Parses results, matches to prompts, stores in memory.
    """
    try:
        body = await request.json()
        if not isinstance(body, list):
            raise HTTPException(status_code=400, detail="Expected array of results")
        items = [BrightDataWebhookItem(**item) for item in body]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    batch_info = registry.get_batch(batch_id)
    if not batch_info:
        logger.warning(f"Batch {batch_id} not found in registry")
        return WebhookResponse(
            status="error",
            batch_id=batch_id,
            processed_count=0,
            failed_count=len(items),
            message=f"Batch {batch_id} not found",
        )

    processed = 0
    failed = 0

    for item in items:
        prompt_id = registry.get_prompt_id_by_text(batch_id, item.input.prompt)
        if not prompt_id:
            logger.warning(f"No prompt_id for: {item.input.prompt[:50]}...")
            registry.add_error(
                batch_id, f"No matching prompt for: {item.input.prompt[:50]}"
            )
            failed += 1
            continue

        # Filter citations (only cited=true)
        citations: list[ParsedCitation] = []
        if item.citations:
            citations = [
                ParsedCitation(
                    url=c.url,
                    title=c.title,
                    description=c.description,
                    domain=c.domain,
                )
                for c in item.citations
                if c.cited
            ]

        result = ParsedResult(
            prompt_id=prompt_id,
            prompt_text=item.input.prompt,
            answer_text=item.answer_text,
            citations=citations,
            model=item.model,
            timestamp=item.timestamp,
        )
        registry.add_result(batch_id, result)
        processed += 1
        logger.info(f"Stored result for prompt {prompt_id}")

    # Mark batch completed
    final_status = BatchStatus.COMPLETED if failed == 0 else BatchStatus.PARTIAL
    registry.complete_batch(batch_id, final_status)

    return WebhookResponse(
        status="success" if failed == 0 else "partial",
        batch_id=batch_id,
        processed_count=processed,
        failed_count=failed,
    )


@router.get("/brightdata/results", response_model=AllBatchesResponse)
async def get_all_brightdata_results(
    registry: InMemoryBatchRegistry = Depends(get_batch_registry),
) -> AllBatchesResponse:
    """
    Get all batches with their parsed results.

    Test endpoint for debugging/verification.
    """
    batches = registry.get_all_batches()

    batch_responses: list[BatchResponse] = []
    for batch in batches:
        results = [
            ResultResponse(
                prompt_id=r.prompt_id,
                prompt_text=r.prompt_text,
                answer_text=r.answer_text,
                citations=[
                    CitationResponse(
                        url=c.url,
                        title=c.title,
                        description=c.description,
                        domain=c.domain,
                    )
                    for c in r.citations
                ],
                model=r.model,
                timestamp=r.timestamp,
            )
            for r in batch.results
        ]
        batch_responses.append(
            BatchResponse(
                batch_id=batch.batch_id,
                user_id=batch.user_id,
                status=batch.status.value,
                created_at=batch.created_at,
                total_prompts=len(batch.prompt_id_to_text),
                results=results,
                errors=batch.errors,
            )
        )

    return AllBatchesResponse(batches=batch_responses, total_batches=len(batch_responses))
