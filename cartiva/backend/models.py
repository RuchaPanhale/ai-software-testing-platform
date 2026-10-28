from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4
from datetime import datetime, timezone

class Product(SQLModel, table=True):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_products_name_not_blank",
        ),
        CheckConstraint(
            "length(trim(category)) > 0",
            name="ck_products_category_not_blank",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=150)
    description: str = Field(default="", max_length=2000)
    category: str = Field(max_length=50, index=True)
    image_url: str | None = Field(default=None, max_length=1000)


class ProductVariant(SQLModel, table=True):
    __tablename__ = "product_variants"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "size",
            "color",
            name="uq_product_variants_product_size_color",
        ),
        CheckConstraint(
            "price_cents >= 0",
            name="ck_product_variants_price_nonnegative",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_variants_stock_nonnegative",
        ),
        CheckConstraint(
            "length(trim(size)) > 0",
            name="ck_product_variants_size_not_blank",
        ),
        CheckConstraint(
            "length(trim(color)) > 0",
            name="ck_product_variants_color_not_blank",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    size: str = Field(max_length=30)
    color: str = Field(max_length=50, index=True)
    price_cents: int
    stock_quantity: int = Field(default=0)
    image_url: str | None = Field(default=None, max_length=1000)


class Cart(SQLModel, table=True):
    __tablename__ = "carts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "variant_id",
            name="uq_cart_items_cart_variant",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_cart_items_quantity_positive",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    cart_id: UUID = Field(foreign_key="carts.id", index=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    quantity: int = Field(gt=0)


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            name="uq_orders_cart_id",
        ),
        CheckConstraint(
            "subtotal_cents >= 0",
            name="ck_orders_subtotal_nonnegative",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cart_id: UUID = Field(foreign_key="carts.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    subtotal_cents: int = Field(ge=0)


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "variant_id",
            name="uq_order_items_order_variant",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price_cents >= 0",
            name="ck_order_items_price_nonnegative",
        ),
        CheckConstraint(
            "line_total_cents = unit_price_cents * quantity",
            name="ck_order_items_line_total_matches",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    order_id: UUID = Field(foreign_key="orders.id", index=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)

    # Snapshot fields preserve what was purchased.
    product_name: str = Field(max_length=150)
    size: str = Field(max_length=30)
    color: str = Field(max_length=50)
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)