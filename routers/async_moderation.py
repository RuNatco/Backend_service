from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.sentry import report_exception
from dependencies.auth import get_current_account
from errors import (
    AddNotFoundError,
    KafkaUnavailableError,
    ModerationEnqueueError,
    ModerationTaskNotFoundError,
)
from models.accounts import AccountModel
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


class CloseAddResponse(BaseModel):
    item_id: int
    status: str
    message: str


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(
    request: AsyncPredictRequest,
    http_request: Request,
    current_account: AccountModel = Depends(get_current_account),
) -> AsyncPredictResponse:
    _ = current_account
    kafka_client = getattr(http_request.app.state, "kafka_client", None)
    try:
        task_id, status = await moderation_service.enqueue(
            item_id=request.item_id,
            kafka_client=kafka_client,
        )
    except AddNotFoundError as exc:
        report_exception(exc)
        raise HTTPException(status_code=404, detail="Add not found") from exc
    except KafkaUnavailableError as exc:
        report_exception(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModerationEnqueueError as exc:
        report_exception(exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        report_exception(exc)
        raise HTTPException(status_code=500, detail="Failed to enqueue moderation request") from exc

    return AsyncPredictResponse(
        task_id=task_id,
        status=status,
        message="Moderation request accepted",
    )


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(
    task_id: int,
    http_request: Request,
    current_account: AccountModel = Depends(get_current_account),
) -> ModerationResultResponse:
    _ = current_account
    cache_storage = getattr(http_request.app.state, "prediction_cache", None)
    try:
        result = await moderation_service.get_result(task_id, cache_storage=cache_storage)
    except ModerationTaskNotFoundError as exc:
        report_exception(exc)
        raise HTTPException(status_code=404, detail="Task not found") from exc

    return ModerationResultResponse(
        task_id=result.id,
        status=result.status,
        is_violation=result.is_violation,
        probability=result.probability,
        error_message=result.error_message,
    )


@router.post("/close", response_model=CloseAddResponse)
async def close_add(
    item_id: int,
    http_request: Request,
    current_account: AccountModel = Depends(get_current_account),
) -> CloseAddResponse:
    _ = current_account
    cache_storage = getattr(http_request.app.state, "prediction_cache", None)
    try:
        await moderation_service.close_item(item_id, cache_storage=cache_storage)
    except AddNotFoundError as exc:
        report_exception(exc)
        raise HTTPException(status_code=404, detail="Add not found") from exc

    return CloseAddResponse(
        item_id=item_id,
        status="closed",
        message="Add and predictions removed",
    )
