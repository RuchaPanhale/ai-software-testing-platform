"""Read-only catalog API routes."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from cartiva.backend.database import get_session
from cartiva.backend.models import Product, ProductVariant
from cartiva.backend.schemas import ProductRead, ProductVariantRead


router = APIRouter(prefix="/products", tags=["Catalog"])

SessionDependency = Annotated[Session, Depends(get_session)]


def normalize_text(value: str) -> str:
    """Ignore capitalization and collapse extra whitespace."""
    return " ".join(value.casefold().split())


@router.get("", response_model=list[ProductRead])
def list_products(
    session: SessionDependency,
    q: Annotated[
        str | None,
        Query(description="Search product names, categories, and variant colors."),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="Exact category match, ignoring case and extra spaces."),
    ] = None,
    color: Annotated[
        str | None,
        Query(description="Exact color match, ignoring case and extra spaces."),
    ] = None,
) -> list[ProductRead]:
    """Return products and variants matching all supplied criteria."""

    search_words = normalize_text(q or "").split()
    category_filter = normalize_text(category or "")
    color_filter = normalize_text(color or "")

    products = session.exec(
        select(Product).order_by(Product.name, Product.id)
    ).all()

    if not products:
        return []

    variants = session.exec(
        select(ProductVariant).order_by(ProductVariant.id)
    ).all()

    variants_by_product: dict[int, list[ProductVariant]] = defaultdict(list)

    for variant in variants:
        variants_by_product[variant.product_id].append(variant)

    results: list[ProductRead] = []

    for product in products:
        if (
            category_filter
            and normalize_text(product.category) != category_filter
        ):
            continue

        matching_variants: list[ProductVariantRead] = []

        for variant in variants_by_product[product.id]:
            if color_filter and normalize_text(variant.color) != color_filter:
                continue

            searchable_text = normalize_text(
                f"{product.name} {product.category} {variant.color}"
            )

            if not all(word in searchable_text for word in search_words):
                continue

            matching_variants.append(
                ProductVariantRead.model_validate(variant)
            )

        if not matching_variants:
            continue

        results.append(
            ProductRead(
                id=product.id,
                name=product.name,
                description=product.description,
                category=product.category,
                image_url=product.image_url,
                variants=matching_variants,
            )
        )

    return results