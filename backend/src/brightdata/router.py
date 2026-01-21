"""API router for Bright Data webhook endpoints."""

import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.brightdata.deps import WebhookAuthDep
from src.brightdata.models.api_models import WebhookResponse
from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.strategies import AssistantStrategyFactory, IndexBasedPromptMatcher
from src.database.evals_models import (
    BrightDataBatchStatus,
    EvaluationStatus,
    PromptEvaluation,
)
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations/api/v1", tags=["brightdata"])

# In-memory storage for raw webhook payloads (for debugging)
_last_webhook_payloads: list[dict] = []
MAX_STORED_PAYLOADS = 10


async def _parse_webhook_body(request: Request) -> list[Any]:
    """Parse gzip-compressed webhook body from Bright Data."""
    raw_body = await request.body()
    decompressed = gzip.decompress(raw_body)
    body = json.loads(decompressed)
    logger.info(f"Webhook body parsed, items count: {len(body) if isinstance(body, list) else 'not a list'}")
    return body


@router.post("/webhook/{assistant_key}/{batch_id}", response_model=WebhookResponse)
async def receive_brightdata_webhook(
    assistant_key: str,
    batch_id: str,
    request: Request,
    _auth: WebhookAuthDep,
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
) -> WebhookResponse:
    """
    Receive webhook from Bright Data with scraping results.

    This endpoint is called by Bright Data when scraping completes.
    Parses gzip-compressed results, matches to prompts via index, creates PromptEvaluation records.

    Args:
        assistant_key: URL-safe assistant identifier (e.g., "chatgpt", "perplexity")
        batch_id: Unique batch identifier
    """
    # Get strategy for this assistant
    try:
        strategy = AssistantStrategyFactory.get_strategy_by_key(assistant_key)
    except ValueError as e:
        logger.error(f"Unknown assistant key: {assistant_key}")
        raise HTTPException(status_code=400, detail=str(e))

    # Parse gzip body
    try:
        body = await _parse_webhook_body(request)
    except Exception as e:
        logger.error(f"Webhook parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Store raw payload for debugging
    logger.info(f"Webhook full payload: {json.dumps(body, indent=2, default=str)}")
    _last_webhook_payloads.append({
        "batch_id": batch_id,
        "assistant_key": assistant_key,
        "payload": body,
    })
    if len(_last_webhook_payloads) > MAX_STORED_PAYLOADS:
        _last_webhook_payloads.pop(0)

    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Expected array of results")

    # Get batch from database
    batch_service = BrightDataBatchService(evals_session)
    batch = await batch_service.get_batch(batch_id)
    if not batch:
        logger.warning(f"Batch {batch_id} not found in database")
        return WebhookResponse(
            status=BrightDataBatchStatus.FAILED.value,
            batch_id=batch_id,
            processed_count=0,
            failed_count=len(body),
            message=f"Batch {batch_id} not found",
        )

    # Create index-based matcher from batch's index_to_prompt_id
    index_to_prompt_id = batch.index_to_prompt_id or {}
    matcher = IndexBasedPromptMatcher(index_to_prompt_id)

    # Get assistant_id and country_id from batch (set during trigger)
    assistant_id = batch.assistant_id
    country_id = batch.country_id

    processed = 0
    failed = 0
    now = datetime.now(timezone.utc)

    for raw_item in body:
        # Parse webhook item using strategy
        parsed = strategy.parse_webhook_item(raw_item)

        # Match prompt by index
        prompt_id = matcher.match(parsed)
        if not prompt_id:
            logger.warning(
                f"No prompt_id for index={parsed.index}, prompt={parsed.prompt_text[:50]}..."
            )
            failed += 1
            continue

        # Create PromptEvaluation record with country_id
        evaluation = PromptEvaluation(
            prompt_id=prompt_id,
            assistant_id=assistant_id,
            country_id=country_id,
            status=EvaluationStatus.COMPLETED,
            claimed_at=now,
            completed_at=now,
            answer={
                "response": parsed.answer_text,
                "citations": parsed.citations,
                "timestamp": now.isoformat(),
            },
        )
        evals_session.add(evaluation)
        processed += 1
        logger.info(f"Created evaluation for prompt {prompt_id} with country_id={country_id}")

    # Commit all evaluations
    await evals_session.commit()

    # Mark batch completed
    final_status = BrightDataBatchStatus.COMPLETED if failed == 0 else BrightDataBatchStatus.PARTIAL
    await batch_service.complete_batch(batch_id, final_status)
    await evals_session.commit()

    # Check if this batch is part of a daily scheduled batch
    try:
        from src.daily_scheduling.services.batch_completion_service import BatchCompletionService
        completion_service = BatchCompletionService(evals_session)
        await completion_service.on_brightdata_batch_completed(batch_id)
    except Exception as e:
        logger.warning(f"Failed to check daily batch completion: {e}")

    # Check if this batch is part of a manual report request
    try:
        from src.reports.services.report_request_service import ReportRequestService
        request_service = ReportRequestService(prompts_session, evals_session)
        await request_service.on_brightdata_completed(batch_id)
    except Exception as e:
        logger.warning(f"Failed to check report request completion: {e}")

    return WebhookResponse(
        status=final_status.value,
        batch_id=batch_id,
        processed_count=processed,
        failed_count=failed,
    )


@router.get("/webhook/debug/payloads")
async def get_debug_webhook_payloads() -> dict:
    """
    Get last received webhook payloads for debugging.

    Returns the last 10 raw payloads received by the webhook endpoint.
    Useful for understanding the structure of Bright Data responses.
    """
    return {
        "count": len(_last_webhook_payloads),
        "payloads": _last_webhook_payloads,
    }
