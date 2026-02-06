from pydantic import BaseModel, Field


class AddModel(BaseModel):
    id: int
    seller_id: int
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int
    images_qty: int = Field(..., ge=0)
