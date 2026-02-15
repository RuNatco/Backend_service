from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.predict import PredictService, predict_violation
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
async def predict(request: PredictRequest, http_request: Request) -> PredictResponse:
    try:
        model = getattr(http_request.app.state, "model", None)
        if model is None:
            raise HTTPException(status_code=503, detail="Model is not loaded")

        is_violation, probability = predict_violation(
            model=model,
            seller_id=request.seller_id,
            item_id=request.item_id,
            is_verified_seller=request.is_verified_seller,
            images_qty=request.images_qty,
            description=request.description,
            category=request.category,
        )

        return PredictResponse(is_violation=is_violation, probability=probability)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail='Prediction failed') from exc


@router.get('/simple_predict', response_model=PredictResponse, summary='Predict by item_id only')
async def simple_predict(item_id: int, http_request: Request) -> PredictResponse:
    try:
        model = getattr(http_request.app.state, "model", None)
        if model is None:
            raise HTTPException(status_code=503, detail="Model is not loaded")

        is_violation, probability = await predict_service.predict_by_item_id(
            item_id=item_id,
            model=model,
        )

        return PredictResponse(is_violation=is_violation, probability=probability)
    except AddNotFoundError:
        raise HTTPException(status_code=404, detail="Add or seller not found")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail='Prediction failed') from exc

