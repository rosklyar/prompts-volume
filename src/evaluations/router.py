"""API router for evaluations endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.config.settings import settings
from src.database.models import Topic
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.evaluations.models.api_models import (
    AddPriorityPromptsRequest,
    AddPriorityPromptsResponse,
    EvaluationResultItem,
    GetResultsRequest,
    GetResultsResponse,
    PollRequest,
    PollResponse,
    PriorityPromptResult,
    ReleaseRequest,
    ReleaseResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from src.evaluations.services.evaluation_service import (
    EvaluationService,
    get_evaluation_service,
)
from src.evaluations.services.priority_prompt_service import (
    PriorityPromptService,
    get_priority_prompt_service,
)

router = APIRouter(prefix="/evaluations/api/v1", tags=["evaluations"])


@router.post("/poll", response_model=PollResponse)
async def poll_for_evaluation(
    request: PollRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> PollResponse:
    """
    Poll for a single prompt that needs evaluation.

    Returns exactly 1 prompt (or null fields if none available).
    Uses PostgreSQL locking (CAS) to prevent race conditions.

    Validates assistant_name and plan_name against database.
    """
    # Validate assistant/plan combination and get assistant_plan_id
    assistant_plan_id = await evaluation_service.get_assistant_plan_id(
        assistant_name=request.assistant_name,
        plan_name=request.plan_name,
    )

    if assistant_plan_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid assistant/plan combination: "
                f"assistant_name='{request.assistant_name}', "
                f"plan_name='{request.plan_name}'"
            )
        )

    evaluation = await evaluation_service.poll_for_prompt(
        assistant_plan_id=assistant_plan_id,
    )

    if not evaluation:
        # No prompts available
        return PollResponse()

    return PollResponse(
        evaluation_id=evaluation.id,
        prompt_id=evaluation.prompt_id,
        prompt_text=evaluation.prompt.prompt_text,
        topic_id=evaluation.prompt.topic_id,
        claimed_at=evaluation.claimed_at,
    )


@router.post("/submit", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> SubmitAnswerResponse:
    """
    Submit evaluation answer and mark as completed.

    Answer must include: response, citations, timestamp.
    """
    evaluation = await evaluation_service.submit_answer(
        evaluation_id=request.evaluation_id,
        answer=request.answer.model_dump(),
    )

    return SubmitAnswerResponse(
        evaluation_id=evaluation.id,
        prompt_id=evaluation.prompt_id,
        status=evaluation.status.value,
        completed_at=evaluation.completed_at,
    )


@router.post("/release", response_model=ReleaseResponse)
async def release_evaluation(
    request: ReleaseRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> ReleaseResponse:
    """
    Release claimed evaluation on failure.

    Can either delete (make available again) or mark as failed.
    """
    if request.mark_as_failed and not request.failure_reason:
        raise HTTPException(
            status_code=422,
            detail="failure_reason required when mark_as_failed=true"
        )

    evaluation_id, action = await evaluation_service.release_evaluation(
        evaluation_id=request.evaluation_id,
        mark_as_failed=request.mark_as_failed,
        failure_reason=request.failure_reason,
    )

    return ReleaseResponse(
        evaluation_id=evaluation_id,
        action=action,
    )


@router.post("/results", response_model=GetResultsResponse)
async def get_latest_results(
    request: GetResultsRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> GetResultsResponse:
    """
    Get latest evaluation results for a list of prompt IDs.

    Returns the most recent COMPLETED evaluation for each prompt_id
    that has been evaluated with the specified assistant/plan.
    """
    # Validate assistant/plan combination and get assistant_plan_id
    assistant_plan_id = await evaluation_service.get_assistant_plan_id(
        assistant_name=request.assistant_name,
        plan_name=request.plan_name,
    )

    if assistant_plan_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid assistant/plan combination: "
                f"assistant_name='{request.assistant_name}', "
                f"plan_name='{request.plan_name}'"
            )
        )

    prompt_eval_pairs = await evaluation_service.get_latest_results(
        assistant_plan_id=assistant_plan_id,
        prompt_ids=request.prompt_ids,
    )

    results = [
        EvaluationResultItem(
            prompt_id=prompt.id,
            prompt_text=prompt.prompt_text,
            evaluation_id=evaluation.id if evaluation else None,
            status=evaluation.status.value if evaluation else None,
            answer=evaluation.answer if evaluation else None,
            completed_at=evaluation.completed_at if evaluation else None,
        )
        for prompt, evaluation in prompt_eval_pairs
    ]

    return GetResultsResponse(results=results)


@router.post("/priority-prompts", response_model=AddPriorityPromptsResponse)
async def add_priority_prompts(
    request: AddPriorityPromptsRequest,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
) -> AddPriorityPromptsResponse:
    """
    Add new prompts with priority evaluation.

    - Accepts list of prompt texts (up to configured max)
    - Checks for duplicates using similarity >= 0.99
    - Creates new prompts with embeddings
    - Adds to priority queue (polled first)
    - Allows null topic_id
    """
    # Validate batch size
    if len(request.prompts) > settings.max_priority_prompts_per_request:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Batch size {len(request.prompts)} exceeds maximum "
                f"{settings.max_priority_prompts_per_request}"
            )
        )

    # Validate topic_id if provided
    if request.topic_id is not None:
        topic_query = select(Topic).where(Topic.id == request.topic_id)
        result = await evaluation_service.session.execute(topic_query)
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail=f"Topic with id={request.topic_id} not found"
            )

    # Create service
    priority_service = get_priority_prompt_service(
        evaluation_service.session,
        embeddings_service,
        settings.max_priority_prompts_per_request,
    )

    # Process prompts
    prompt_texts = [p.prompt_text for p in request.prompts]
    result = await priority_service.add_priority_prompts(
        prompt_texts=prompt_texts,
        topic_id=request.topic_id,
    )

    # Build response
    return AddPriorityPromptsResponse(
        created_count=result["created_count"],
        reused_count=result["reused_count"],
        total_count=result["total_count"],
        prompts=[PriorityPromptResult(**p) for p in result["prompts"]],
        request_id=result["request_id"],
    )
