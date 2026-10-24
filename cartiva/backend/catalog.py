"""Read-only catalog API routes."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from cartiva.backend.database import get_session
from cartiva.backend.models import Product, ProductVariant
from cartiva.backend.schemas import ProductRead, ProductVariantRead


router = APIRouter(prefix="/products", tags=["Catalog"])

SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[ProductRead])
def list_products(session: SessionDependency) -> list[ProductRead]:
    """Return products with their available and sold-out variants."""

    products = session.exec(
        select(Product).order_by(Product.name, Product.id)
    ).all()

    if not products:
        return []

    variants = session.exec(
        select(ProductVariant).order_by(ProductVariant.id)
    ).all()

    variants_by_product: dict[int, list[ProductVariantRead]] = defaultdict(list)

    for variant in variants:
        variants_by_product[variant.product_id].append(
            ProductVariantRead.model_validate(variant)
        )

    return [
        ProductRead(
            id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            image_url=product.image_url,
            variants=variants_by_product[product.id],
        )
        for product in products
    ]