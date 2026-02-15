from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from errors import (
    AddNotFoundError,
    KafkaUnavailableError,
    ModerationEnqueueError,
    ModerationTaskNotFoundError,
)
from services.moderation import ModerationService


router = APIRouter()
moderation_service = ModerationService()


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
    kafka_client = getattr(http_request.app.state, "kafka_client", None)
    try:
        task_id, status = await moderation_service.enqueue(
            item_id=request.item_id,
            kafka_client=kafka_client,
        )
    except AddNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Add not found") from exc
    except KafkaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModerationEnqueueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to enqueue moderation request") from exc

    return AsyncPredictResponse(
        task_id=task_id,
        status=status,
        message="Moderation request accepted",
    )


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int) -> ModerationResultResponse:
    try:
        result = await moderation_service.get_result(task_id)
    except ModerationTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc

    return ModerationResultResponse(
        task_id=result.id,
        status=result.status,
        is_violation=result.is_violation,
        probability=result.probability,
        error_message=result.error_message,
    )
