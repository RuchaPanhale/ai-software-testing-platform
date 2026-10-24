"""Public response formats for the Cartiva API."""

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    size: str
    color: str
    price_cents: int = Field(ge=0)
    stock_quantity: int = Field(ge=0)
    image_url: str | None


class ProductRead(BaseModel):
    id: int
    name: str
    description: str
    category: str
    image_url: str | None
    variants: list[ProductVariantRead]