from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ModerationResultModel(BaseModel):
    id: int
    item_id: int
    status: str
    is_violation: Optional[bool] = None
    probability: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
