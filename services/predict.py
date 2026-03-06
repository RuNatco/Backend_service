import logging
from dataclasses import dataclass
from typing import Tuple, Any, Optional

import numpy as np
from app.metrics import observe_prediction_result, track_prediction_duration
from errors import AddNotFoundError
from repositories.adds import AddRepository
from storages.prediction_cache import PredictionCacheStorage

logger = logging.getLogger(__name__)


def build_features(
    is_verified_seller: bool,
    images_qty: int,
    description: str,
    category: int,
) -> np.ndarray:
    return np.array([[
        1.0 if is_verified_seller else 0.0,
        images_qty / 10.0,
        len(description) / 1000.0,
        category / 100.0,
    ]], dtype=float)


def predict_violation(
    model: Any,
    seller_id: int,
    item_id: int,
    is_verified_seller: bool,
    images_qty: int,
    description: str,
    category: int,
) -> Tuple[bool, float]:
    features = build_features(
        is_verified_seller=is_verified_seller,
        images_qty=images_qty,
        description=description,
        category=category,
    )

    logger.info(
        "predict_request seller_id=%s item_id=%s features=%s",
        seller_id,
        item_id,
        features.tolist()[0],
    )

    with track_prediction_duration():
        probability = float(model.predict_proba(features)[0][1])
        is_violation = bool(model.predict(features)[0])

    logger.info(
        "predict_response is_violation=%s probability=%.6f",
        is_violation,
        probability,
    )

    return is_violation, probability


@dataclass(frozen=True)
class PredictService:
    add_repo: AddRepository = AddRepository()

    @staticmethod
    def _result_dict(is_violation: bool, probability: float) -> dict[str, Any]:
        return {
            "is_violation": bool(is_violation),
            "probability": float(probability),
        }

    async def predict_by_item_id(
        self,
        *,
        item_id: int,
        model: Any,
        cache_storage: Optional[PredictionCacheStorage] = None,
    ) -> Tuple[bool, float]:
        if cache_storage is not None:
            cached = await cache_storage.get_simple_prediction(item_id)
            if cached is not None:
                return bool(cached["is_violation"]), float(cached["probability"])

        add_with_seller = await self.add_repo.get_with_seller(item_id)

        is_violation, probability = predict_violation(
            model=model,
            seller_id=int(add_with_seller["seller_id"]),
            item_id=int(add_with_seller["add_id"]),
            is_verified_seller=bool(add_with_seller["is_verified_seller"]),
            images_qty=int(add_with_seller["images_qty"]),
            description=str(add_with_seller["description"]),
            category=int(add_with_seller["category"]),
        )
        if cache_storage is not None:
            await cache_storage.set_simple_prediction(
                item_id,
                self._result_dict(is_violation, probability),
            )
        observe_prediction_result(is_violation, probability)
        return is_violation, probability

    async def predict_from_payload(
        self,
        *,
        payload: dict[str, Any],
        model: Any,
        cache_storage: Optional[PredictionCacheStorage] = None,
    ) -> Tuple[bool, float]:
        item_id = int(payload["item_id"])
        if cache_storage is not None:
            cached = await cache_storage.get_sync_prediction(
                item_id=item_id,
                payload=payload,
            )
            if cached is not None:
                return bool(cached["is_violation"]), float(cached["probability"])

        is_violation, probability = predict_violation(
            model=model,
            seller_id=int(payload["seller_id"]),
            item_id=item_id,
            is_verified_seller=bool(payload["is_verified_seller"]),
            images_qty=int(payload["images_qty"]),
            description=str(payload["description"]),
            category=int(payload["category"]),
        )
        if cache_storage is not None:
            await cache_storage.set_sync_prediction(
                item_id=item_id,
                payload=payload,
                result=self._result_dict(is_violation, probability),
            )
        observe_prediction_result(is_violation, probability)
        return is_violation, probability
