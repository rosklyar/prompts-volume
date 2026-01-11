"""API router for Bright Data webhook endpoints."""

import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from src.brightdata.deps import WebhookAuthDep
from src.brightdata.models.api_models import BrightDataWebhookItem, WebhookResponse
from src.brightdata.services.batch_service import BrightDataBatchService
from src.database.evals_models import (
    AIAssistant,
    AIAssistantPlan,
    BrightDataBatchStatus,
    EvaluationStatus,
    PromptEvaluation,
)
from src.database.evals_session import get_evals_session
from src.database.models import Prompt
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


async def _get_chatgpt_free_plan_id(session: AsyncSession) -> int:
    """Get ChatGPT Free assistant plan ID."""
    result = await session.execute(
        select(AIAssistantPlan.id)
        .join(AIAssistant, AIAssistantPlan.assistant_id == AIAssistant.id)
        .where(func.upper(AIAssistant.name) == "CHATGPT")
        .where(func.upper(AIAssistantPlan.name) == "FREE")
    )
    plan_id = result.scalar_one_or_none()
    if not plan_id:
        raise HTTPException(status_code=500, detail="ChatGPT Free assistant plan not found")
    return plan_id


async def _get_prompts_by_ids(
    session: AsyncSession,
    prompt_ids: list[int],
) -> list[Prompt]:
    """Get prompts by IDs from prompts database."""
    result = await session.execute(
        select(Prompt).where(Prompt.id.in_(prompt_ids))
    )
    return list(result.scalars().all())


@router.post("/webhook/{batch_id}", response_model=WebhookResponse)
async def receive_brightdata_webhook(
    batch_id: str,
    request: Request,
    _auth: WebhookAuthDep,
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
) -> WebhookResponse:
    """
    Receive webhook from Bright Data with scraping results.

    This endpoint is called by Bright Data when scraping completes.
    Parses gzip-compressed results, matches to prompts, creates PromptEvaluation records.
    """
    # Parse gzip body
    try:
        body = await _parse_webhook_body(request)
    except Exception as e:
        logger.error(f"Webhook parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Store raw payload for debugging
    logger.info(f"Webhook full payload: {json.dumps(body, indent=2, default=str)}")
    _last_webhook_payloads.append({"batch_id": batch_id, "payload": body})
    if len(_last_webhook_payloads) > MAX_STORED_PAYLOADS:
        _last_webhook_payloads.pop(0)

    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Expected array of results")

    # Validate payload structure
    try:
        items = [BrightDataWebhookItem(**item) for item in body]
    except Exception as e:
        logger.error(f"Webhook payload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Get batch from database
    batch_service = BrightDataBatchService(evals_session)
    batch = await batch_service.get_batch(batch_id)
    if not batch:
        logger.warning(f"Batch {batch_id} not found in database")
        return WebhookResponse(
            status=BrightDataBatchStatus.FAILED.value,
            batch_id=batch_id,
            processed_count=0,
            failed_count=len(items),
            message=f"Batch {batch_id} not found",
        )

    # Get prompts for text matching
    prompts = await _get_prompts_by_ids(prompts_session, batch.prompt_ids)
    text_to_prompt_id = {p.prompt_text: p.id for p in prompts}

    # Get ChatGPT Free assistant plan (hardcoded for now)
    assistant_plan_id = await _get_chatgpt_free_plan_id(evals_session)

    processed = 0
    failed = 0
    now = datetime.now(timezone.utc)

    for item in items:
        # Match prompt by text
        prompt_id = text_to_prompt_id.get(item.prompt)
        if not prompt_id:
            logger.warning(f"No prompt_id for: {item.prompt[:50]}...")
            failed += 1
            continue

        # Filter to only include citations actually used in the answer
        citations = [
            {
                "url": c.url,
                "text": c.title,
                "domain": c.domain,
            }
            for c in (item.citations or [])
            if c.cited
        ]

        # Create PromptEvaluation record
        evaluation = PromptEvaluation(
            prompt_id=prompt_id,
            assistant_plan_id=assistant_plan_id,
            status=EvaluationStatus.COMPLETED,
            claimed_at=now,
            completed_at=now,
            answer={
                "response": item.answer_text,
                "citations": citations,
                "timestamp": now.isoformat(),
            },
        )
        evals_session.add(evaluation)
        processed += 1
        logger.info(f"Created evaluation for prompt {prompt_id}")

    # Commit all evaluations
    await evals_session.commit()

    # Mark batch completed
    final_status = BrightDataBatchStatus.COMPLETED if failed == 0 else BrightDataBatchStatus.PARTIAL
    await batch_service.complete_batch(batch_id, final_status)
    await evals_session.commit()

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
