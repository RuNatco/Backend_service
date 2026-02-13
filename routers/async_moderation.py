from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from errors import AddNotFoundError, ModerationTaskNotFoundError
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository


router = APIRouter()
add_repo = AddRepository()
moderation_repo = ModerationResultRepository()


class AsyncPredictRequest(BaseModel):
    item_id: int = Field(..., description="Add id")


class AsyncPredictResponse(BaseModel):
    task_id: int
    status: str
    message: str


class ModerationResultResponse(BaseModel):
    task_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
    error_message: Optional[str] = None


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(request: AsyncPredictRequest, http_request: Request) -> AsyncPredictResponse:
    try:
        await add_repo.get(request.item_id)
    except AddNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Add not found") from exc

    moderation_task = await moderation_repo.create_pending(request.item_id)

    kafka_client = getattr(http_request.app.state, "kafka_client", None)
    if kafka_client is None:
        raise HTTPException(status_code=503, detail="Kafka is unavailable")

    try:
        await kafka_client.send_moderation_request(
            item_id=request.item_id,
            task_id=moderation_task.id,
        )
    except Exception as exc:
        await moderation_repo.mark_failed(moderation_task.id, str(exc))
        raise HTTPException(status_code=500, detail="Failed to enqueue moderation request") from exc

    return AsyncPredictResponse(
        task_id=moderation_task.id,
        status=moderation_task.status,
        message="Moderation request accepted",
    )


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int) -> ModerationResultResponse:
    try:
        result = await moderation_repo.get(task_id)
    except ModerationTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc

    return ModerationResultResponse(
        task_id=result.id,
        status=result.status,
        is_violation=result.is_violation,
        probability=result.probability,
        error_message=result.error_message,
    )
