"""API tests using an isolated in-memory database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from cartiva.backend.database import get_session
from cartiva.backend.main import app
from cartiva.backend.models import Product, ProductVariant


@pytest.fixture
def catalog_environment():
    """Give each test a fresh database and API client."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def test_empty_catalog_returns_empty_list(catalog_environment):
    client, _ = catalog_environment

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_catalog_orders_products_and_groups_variants(catalog_environment):
    client, engine = catalog_environment

    with Session(engine) as session:
        # Insert in reverse alphabetical order to test API sorting.
        tote = Product(
            name="Zipper Tote",
            description="A canvas tote.",
            category="Accessories",
        )
        shirt = Product(
            name="Everyday Shirt",
            description="A cotton shirt.",
            category="Shirts",
        )
        session.add_all([tote, shirt])
        session.flush()

        tote_id = tote.id
        shirt_id = shirt.id

        session.add_all(
            [
                ProductVariant(
                    product_id=tote_id,
                    size="One Size",
                    color="Ivory",
                    price_cents=1999,
                    stock_quantity=10,
                ),
                ProductVariant(
                    product_id=shirt_id,
                    size="S",
                    color="Green",
                    price_cents=2999,
                    stock_quantity=8,
                ),
                ProductVariant(
                    product_id=shirt_id,
                    size="M",
                    color="Green",
                    price_cents=2999,
                    stock_quantity=0,
                ),
            ]
        )
        session.commit()

    response = client.get("/products")

    assert response.status_code == 200
    products = response.json()

    assert [product["name"] for product in products] == [
        "Everyday Shirt",
        "Zipper Tote",
    ]
    assert [product["id"] for product in products] == [shirt_id, tote_id]

    shirt_variants = products[0]["variants"]
    tote_variants = products[1]["variants"]

    assert len(shirt_variants) == 2
    assert len(tote_variants) == 1
    assert tote_variants[0]["color"] == "Ivory"

    assert [variant["size"] for variant in shirt_variants] == ["S", "M"]
    assert all(variant["color"] == "Green" for variant in shirt_variants)
    assert all(variant["price_cents"] == 2999 for variant in shirt_variants)

    # Sold-out variants must remain visible in the catalog.
    sold_out = next(
        variant for variant in shirt_variants if variant["size"] == "M"
    )
    assert sold_out["stock_quantity"] == 0
    assert sold_out["image_url"] is None