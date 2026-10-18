from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


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