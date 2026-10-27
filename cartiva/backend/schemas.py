"""Public response formats for the Cartiva API."""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


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


class CartCreated(BaseModel):
    id: UUID


class CartItemAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, strict=True)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: UUID
    variant_id: int
    quantity: int = Field(gt=0)


class CartItemDetail(BaseModel):
    id: int
    variant_id: int
    product_id: int
    product_name: str
    size: str
    color: str
    image_url: str | None
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)
    stock_quantity: int = Field(ge=0)
    has_enough_stock: bool


class CartRead(BaseModel):
    id: UUID
    items: list[CartItemDetail]
    subtotal_cents: int = Field(ge=0)