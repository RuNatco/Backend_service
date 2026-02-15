import logging
from dataclasses import dataclass
from typing import Tuple, Any

import numpy as np
from errors import AddNotFoundError
from repositories.adds import AddRepository

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

    async def predict_by_item_id(
        self,
        *,
        item_id: int,
        model: Any,
    ) -> Tuple[bool, float]:
        add_with_seller = await self.add_repo.get_with_seller(item_id)

        return predict_violation(
            model=model,
            seller_id=int(add_with_seller["seller_id"]),
            item_id=int(add_with_seller["add_id"]),
            is_verified_seller=bool(add_with_seller["is_verified_seller"]),
            images_qty=int(add_with_seller["images_qty"]),
            description=str(add_with_seller["description"]),
            category=int(add_with_seller["category"]),
        )
