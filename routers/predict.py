from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import logging
import numpy as np


class PredictRequest(BaseModel):
    seller_id: int = Field(..., description='Unique seller identifier')
    is_verified_seller: bool = Field(..., description='Seller verification status')
    item_id: int = Field(..., description='Unique item identifier')
    name: str = Field(..., min_length=1, description='Item name')
    description: str = Field(..., min_length=1, description='Item description')
    category: int = Field(..., description='Category identifier')
    images_qty: int = Field(..., ge=0, description='Number of attached images')


logger = logging.getLogger(__name__)

router = APIRouter(prefix='/predict')


class PredictResponse(BaseModel):
    is_violation: bool
    probability: float


@router.post('/', response_model=PredictResponse, summary='Predict if listing is violating')
async def predict(request: PredictRequest, http_request: Request) -> PredictResponse:
    try:
        model = getattr(http_request.app.state, "model", None)
        if model is None:
            raise HTTPException(status_code=503, detail="Model is not loaded")

        features = np.array([[
            1.0 if request.is_verified_seller else 0.0,
            request.images_qty / 10.0,
            len(request.description) / 1000.0,
            request.category / 100.0,
        ]], dtype=float)

        logger.info(
            "predict_request seller_id=%s item_id=%s features=%s",
            request.seller_id,
            request.item_id,
            features.tolist()[0],
        )

        probability = float(model.predict_proba(features)[0][1])
        is_violation = bool(model.predict(features)[0])

        logger.info(
            "predict_response is_violation=%s probability=%.6f",
            is_violation,
            probability,
        )

        return PredictResponse(is_violation=is_violation, probability=probability)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail='Prediction failed') from exc

