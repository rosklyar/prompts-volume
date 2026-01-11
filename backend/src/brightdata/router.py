"""API router for Bright Data webhook endpoints."""

import gzip
import json
import logging
from typing import Any

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


async def _parse_webhook_body(request: Request) -> list[Any]:
    """Parse webhook body - handles gzip, multipart, and raw JSON.

    Bright Data may send data as:
    - gzip-compressed JSON (content-encoding: gzip)
    - multipart/form-data file upload
    - raw JSON body
    """
    content_type = request.headers.get("content-type", "")
    content_encoding = request.headers.get("content-encoding", "")
    logger.info(f"Webhook received - Content-Type: {content_type}, Content-Encoding: {content_encoding}")
    logger.debug(f"Webhook headers: {dict(request.headers)}")

    # Try multipart form data (file upload)
    if "multipart/form-data" in content_type:
        logger.info("Parsing as multipart/form-data")
        form = await request.form()
        form_keys = list(form.keys())
        logger.info(f"Form fields received: {form_keys}")

        # Try common field names
        for field_name in ("file", "data", "results"):
            if field_name in form:
                file = form[field_name]
                logger.info(f"Found file in field '{field_name}', filename: {getattr(file, 'filename', 'N/A')}")
                content = await file.read()
                logger.info(f"File content size: {len(content)} bytes")
                logger.debug(f"File content preview: {content[:500]}...")
                return json.loads(content)

        raise ValueError(f"No file found in multipart form data. Available fields: {form_keys}")

    # Handle gzip-compressed body
    if content_encoding == "gzip":
        logger.info("Decompressing gzip body")
        raw_body = await request.body()
        decompressed = gzip.decompress(raw_body)
        body = json.loads(decompressed)
        logger.info(f"Gzip body parsed, items count: {len(body) if isinstance(body, list) else 'not a list'}")
        return body

    # Fall back to raw JSON body
    logger.info("Parsing as raw JSON body")
    body = await request.json()
    logger.info(f"JSON body parsed, items count: {len(body) if isinstance(body, list) else 'not a list'}")
    return body


def _process_webhook_item(
    item: BrightDataWebhookItem,
    registry: InMemoryBatchRegistry,
    batch_id: str,
) -> ParsedResult | None:
    """Process a single webhook item. Returns None if prompt not found."""
    prompt_id = registry.get_prompt_id_by_text(batch_id, item.input.prompt)
    if not prompt_id:
        logger.warning(f"No prompt_id for: {item.input.prompt[:50]}...")
        registry.add_error(batch_id, f"No matching prompt for: {item.input.prompt[:50]}")
        return None

    # Filter to only include citations actually used in the answer
    # (Bright Data returns all potential citations, cited=True means it was referenced)
    citations = [
        ParsedCitation.from_brightdata_citation(c)
        for c in (item.citations or [])
        if c.cited
    ]

    return ParsedResult(
        prompt_id=prompt_id,
        prompt_text=item.input.prompt,
        answer_text=item.answer_text,
        citations=citations,
        model=item.model,
        timestamp=item.timestamp,
    )


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
    Supports both multipart/form-data (file upload) and raw JSON body.
    Parses results, matches to prompts, stores in memory.
    """
    # Parse body (file upload or raw JSON)
    try:
        body = await _parse_webhook_body(request)
    except Exception as e:
        logger.error(f"Webhook parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Expected array of results")

    # Validate payload structure
    try:
        items = [BrightDataWebhookItem(**item) for item in body]
    except Exception as e:
        logger.error(f"Webhook payload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    batch_info = registry.get_batch(batch_id)
    if not batch_info:
        logger.warning(f"Batch {batch_id} not found in registry")
        return WebhookResponse(
            status=BatchStatus.FAILED.value,
            batch_id=batch_id,
            processed_count=0,
            failed_count=len(items),
            message=f"Batch {batch_id} not found",
        )

    processed = 0
    failed = 0

    for item in items:
        result = _process_webhook_item(item, registry, batch_id)
        if result is None:
            failed += 1
            continue
        registry.add_result(batch_id, result)
        processed += 1
        logger.info(f"Stored result for prompt {result.prompt_id}")

    # Mark batch completed
    final_status = BatchStatus.COMPLETED if failed == 0 else BatchStatus.PARTIAL
    registry.complete_batch(batch_id, final_status)

    return WebhookResponse(
        status=final_status.value,
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
                citations=[CitationResponse.from_parsed(c) for c in r.citations],
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
