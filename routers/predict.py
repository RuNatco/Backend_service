from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    seller_id: int = Field(..., description='Unique seller identifier')
    is_verified_seller: bool = Field(..., description='Seller verification status')
    item_id: int = Field(..., description='Unique item identifier')
    name: str = Field(..., min_length=1, description='Item name')
    description: str = Field(..., min_length=1, description='Item description')
    category: int = Field(..., description='Category identifier')
    images_qty: int = Field(..., ge=0, description='Number of attached images')


router = APIRouter(prefix='/predict')


def apply_prediction_rules(payload: PredictRequest) -> bool:
    """Naive moderation"""
    if payload.is_verified_seller:
        return True
    return payload.images_qty > 0


@router.post('/', response_model=bool, summary='Predict if listing is clean')
async def predict(request: PredictRequest) -> bool:
    try:
        return apply_prediction_rules(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail='Prediction failed') from exc

