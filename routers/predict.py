from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.metrics import observe_prediction_error
from app.sentry import report_exception
from dependencies.auth import get_current_account
from models.accounts import AccountModel
from services.predict import PredictService
from errors import AddNotFoundError


class PredictRequest(BaseModel):
    seller_id: int = Field(..., description='Unique seller identifier')
    is_verified_seller: bool = Field(..., description='Seller verification status')
    item_id: int = Field(..., description='Unique item identifier')
    name: str = Field(..., min_length=1, description='Item name')
    description: str = Field(..., min_length=1, description='Item description')
    category: int = Field(..., description='Category identifier')
    images_qty: int = Field(..., ge=0, description='Number of attached images')


router = APIRouter(prefix='/predict')
predict_service = PredictService()


class PredictResponse(BaseModel):
    is_violation: bool
    probability: float


@router.post('/', response_model=PredictResponse, summary='Predict if listing is violating')
async def predict(
    request: PredictRequest,
    http_request: Request,
    current_account: AccountModel = Depends(get_current_account),
) -> PredictResponse:
    try:
        _ = current_account
        model = getattr(http_request.app.state, "model", None)
        cache_storage = getattr(http_request.app.state, "prediction_cache", None)
        if model is None:
            observe_prediction_error("model_unavailable")
            report_exception(RuntimeError("Model is not loaded"))
            raise HTTPException(status_code=503, detail="Model is not loaded")

        payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        is_violation, probability = await predict_service.predict_from_payload(
            payload=payload,
            model=model,
            cache_storage=cache_storage,
        )

        return PredictResponse(is_violation=is_violation, probability=probability)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        observe_prediction_error("prediction_error")
        report_exception(exc)
        raise HTTPException(status_code=500, detail='Prediction failed') from exc


@router.get('/simple_predict', response_model=PredictResponse, summary='Predict by item_id only')
async def simple_predict(
    item_id: int,
    http_request: Request,
    current_account: AccountModel = Depends(get_current_account),
) -> PredictResponse:
    try:
        _ = current_account
        model = getattr(http_request.app.state, "model", None)
        cache_storage = getattr(http_request.app.state, "prediction_cache", None)
        if model is None:
            observe_prediction_error("model_unavailable")
            report_exception(RuntimeError("Model is not loaded"))
            raise HTTPException(status_code=503, detail="Model is not loaded")

        is_violation, probability = await predict_service.predict_by_item_id(
            item_id=item_id,
            model=model,
            cache_storage=cache_storage,
        )

        return PredictResponse(is_violation=is_violation, probability=probability)
    except AddNotFoundError as exc:
        report_exception(exc)
        raise HTTPException(status_code=404, detail="Add or seller not found")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        observe_prediction_error("prediction_error")
        report_exception(exc)
        raise HTTPException(status_code=500, detail='Prediction failed') from exc

