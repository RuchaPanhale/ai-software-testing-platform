"""Cart API tests using an isolated in-memory database."""

from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from cartiva.backend.models import Cart, CartItem, Product, ProductVariant


def test_create_cart_persists_empty_cart(catalog_environment):
    client, engine = catalog_environment

    response = client.post("/carts")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id"}

    # Parsing also verifies that the response contains a valid UUID.
    cart_id = UUID(body["id"])

    # Use a separate session to verify that the endpoint saved the cart.
    with Session(engine) as session:
        saved_cart = session.get(Cart, cart_id)

        assert saved_cart is not None
        assert saved_cart.id == cart_id

        items = session.exec(
            select(CartItem).where(CartItem.cart_id == cart_id)
        ).all()

        assert items == []


def test_create_cart_requests_produce_distinct_carts(catalog_environment):
    client, engine = catalog_environment

    first_response = client.post("/carts")
    second_response = client.post("/carts")

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_id = UUID(first_response.json()["id"])
    second_id = UUID(second_response.json()["id"])

    assert first_id != second_id

    with Session(engine) as session:
        carts = session.exec(select(Cart)).all()

        assert {cart.id for cart in carts} == {first_id, second_id}


@pytest.fixture
def cart_with_variant(catalog_environment):
    client, engine = catalog_environment

    with Session(engine) as session:
        cart = Cart()
        product = Product(
            name="Everyday Shirt",
            description="A cotton shirt.",
            category="Shirts",
        )
        session.add_all([cart, product])
        session.flush()

        variant = ProductVariant(
            product_id=product.id,
            size="S",
            color="Green",
            price_cents=2999,
            stock_quantity=8,
        )
        session.add(variant)
        session.flush()

        cart_id = cart.id
        variant_id = variant.id
        session.commit()

    return client, engine, cart_id, variant_id


def test_add_item_combines_quantities_without_reserving_stock(
    cart_with_variant,
):
    client, engine, cart_id, variant_id = cart_with_variant
    url = f"/carts/{cart_id}/items"

    first = client.post(
        url,
        json={"variant_id": variant_id, "quantity": 2},
    )

    assert first.status_code == 200
    first_item = first.json()
    assert first_item["cart_id"] == str(cart_id)
    assert first_item["variant_id"] == variant_id
    assert first_item["quantity"] == 2

    # Reach exactly the available stock: 2 + 6 = 8.
    second = client.post(
        url,
        json={"variant_id": variant_id, "quantity": 6},
    )

    assert second.status_code == 200
    assert second.json()["id"] == first_item["id"]
    assert second.json()["quantity"] == 8

    with Session(engine) as session:
        items = session.exec(
            select(CartItem).where(CartItem.cart_id == cart_id)
        ).all()

        assert len(items) == 1
        assert items[0].variant_id == variant_id
        assert items[0].quantity == 8

        variant = session.get(ProductVariant, variant_id)
        assert variant.stock_quantity == 8


def test_add_item_rejects_combined_quantity_above_stock(
    cart_with_variant,
):
    client, engine, cart_id, variant_id = cart_with_variant
    url = f"/carts/{cart_id}/items"

    first = client.post(
        url,
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert first.status_code == 200

    # Seven alone fits stock, but the combined quantity is nine.
    response = client.post(
        url,
        json={"variant_id": variant_id, "quantity": 7},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Requested quantity exceeds available stock"
    }

    with Session(engine) as session:
        items = session.exec(
            select(CartItem).where(CartItem.cart_id == cart_id)
        ).all()

        assert len(items) == 1
        assert items[0].quantity == 2

        variant = session.get(ProductVariant, variant_id)
        assert variant.stock_quantity == 8


@pytest.mark.parametrize(
    "quantity",
    [0, -1, 1.5, "2", True, None],
    ids=[
        "zero",
        "negative",
        "fraction",
        "numeric-string",
        "boolean",
        "null",
    ],
)
def test_add_item_rejects_invalid_quantity(cart_with_variant, quantity):
    client, engine, cart_id, variant_id = cart_with_variant

    response = client.post(
        f"/carts/{cart_id}/items",
        json={"variant_id": variant_id, "quantity": quantity},
    )

    assert response.status_code == 422

    with Session(engine) as session:
        assert session.exec(select(CartItem)).all() == []


def test_add_item_rejects_missing_cart(cart_with_variant):
    client, engine, _, variant_id = cart_with_variant
    missing_cart_id = uuid4()

    response = client.post(
        f"/carts/{missing_cart_id}/items",
        json={"variant_id": variant_id, "quantity": 1},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Cart not found"}

    with Session(engine) as session:
        assert session.exec(select(CartItem)).all() == []


def test_add_item_rejects_missing_variant(cart_with_variant):
    client, engine, cart_id, variant_id = cart_with_variant

    # The fixture creates only one variant.
    missing_variant_id = variant_id + 1

    response = client.post(
        f"/carts/{cart_id}/items",
        json={"variant_id": missing_variant_id, "quantity": 1},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product variant not found"}

    with Session(engine) as session:
        assert session.exec(select(CartItem)).all() == []


@pytest.mark.parametrize(
    "stock, requested_quantity",
    [(0, 1), (8, 9)],
    ids=["sold-out", "first-add-exceeds-stock"],
)
def test_add_item_rejects_unavailable_stock(
    cart_with_variant, stock, requested_quantity
):
    client, engine, cart_id, variant_id = cart_with_variant

    with Session(engine) as session:
        variant = session.get(ProductVariant, variant_id)
        variant.stock_quantity = stock
        session.add(variant)
        session.commit()

    response = client.post(
        f"/carts/{cart_id}/items",
        json={
            "variant_id": variant_id,
            "quantity": requested_quantity,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Requested quantity exceeds available stock"
    }

    with Session(engine) as session:
        assert session.exec(select(CartItem)).all() == []
        variant = session.get(ProductVariant, variant_id)
        assert variant.stock_quantity == stock


def test_add_item_rejects_client_supplied_price(cart_with_variant):
    client, engine, cart_id, variant_id = cart_with_variant

    response = client.post(
        f"/carts/{cart_id}/items",
        json={
            "variant_id": variant_id,
            "quantity": 1,
            "price_cents": 1,
        },
    )

    assert response.status_code == 422

    with Session(engine) as session:
        assert session.exec(select(CartItem)).all() == []
        variant = session.get(ProductVariant, variant_id)
        assert variant.price_cents == 2999

def test_get_empty_cart(catalog_environment):
    client, engine = catalog_environment

    with Session(engine) as session:
        cart = Cart()
        session.add(cart)
        session.commit()
        session.refresh(cart)
        cart_id = cart.id

    response = client.get(f"/carts/{cart_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(cart_id),
        "items": [],
        "subtotal_cents": 0,
    }


def test_get_missing_cart(catalog_environment):
    client, _ = catalog_environment

    response = client.get(f"/carts/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Cart not found"}


def test_get_cart_returns_details_and_totals(cart_with_variant):
    client, engine, cart_id, variant_id = cart_with_variant

    added = client.post(
        f"/carts/{cart_id}/items",
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert added.status_code == 200
    item_id = added.json()["id"]

    with Session(engine) as session:
        variant = session.get(ProductVariant, variant_id)
        product_id = variant.product_id

    response = client.get(f"/carts/{cart_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(cart_id),
        "items": [
            {
                "id": item_id,
                "variant_id": variant_id,
                "product_id": product_id,
                "product_name": "Everyday Shirt",
                "size": "S",
                "color": "Green",
                "image_url": None,
                "quantity": 2,
                "unit_price_cents": 2999,
                "line_total_cents": 5998,
                "stock_quantity": 8,
                "has_enough_stock": True,
            }
        ],
        "subtotal_cents": 5998,
    }


def test_get_cart_uses_current_price_and_flags_low_stock(cart_with_variant):
    client, engine, cart_id, variant_id = cart_with_variant

    added = client.post(
        f"/carts/{cart_id}/items",
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert added.status_code == 200
    item_id = added.json()["id"]

    # Simulate a price change and reduced stock after adding the item.
    with Session(engine) as session:
        variant = session.get(ProductVariant, variant_id)
        variant.price_cents = 3499
        variant.stock_quantity = 1
        session.add(variant)
        session.commit()

    response = client.get(f"/carts/{cart_id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1

    item = body["items"][0]
    assert item["quantity"] == 2
    assert item["unit_price_cents"] == 3499
    assert item["line_total_cents"] == 6998
    assert item["stock_quantity"] == 1
    assert item["has_enough_stock"] is False
    assert body["subtotal_cents"] == 6998

    # Viewing the cart must not change its quantity or inventory.
    with Session(engine) as session:
        saved_item = session.get(CartItem, item_id)
        saved_variant = session.get(ProductVariant, variant_id)

        assert saved_item.quantity == 2
        assert saved_variant.stock_quantity == 1
        assert saved_variant.price_cents == 3499

def test_get_cart_totals_multiple_items_and_excludes_other_carts(
    cart_with_variant,
):
    client, engine, cart_id, shirt_variant_id = cart_with_variant

    with Session(engine) as session:
        tote = Product(
            name="Everyday Tote",
            description="A canvas tote.",
            category="Accessories",
        )
        other_cart = Cart()
        session.add_all([tote, other_cart])
        session.flush()

        tote_variant = ProductVariant(
            product_id=tote.id,
            size="One Size",
            color="Ivory",
            price_cents=1999,
            stock_quantity=10,
        )
        session.add(tote_variant)
        session.flush()

        tote_variant_id = tote_variant.id
        other_cart_id = other_cart.id
        session.commit()

    # Our cart: two shirts and three totes.
    for variant_id, quantity in [
        (shirt_variant_id, 2),
        (tote_variant_id, 3),
    ]:
        response = client.post(
            f"/carts/{cart_id}/items",
            json={"variant_id": variant_id, "quantity": quantity},
        )
        assert response.status_code == 200

    # Another cart contains the same shirt variant.
    response = client.post(
        f"/carts/{other_cart_id}/items",
        json={"variant_id": shirt_variant_id, "quantity": 1},
    )
    assert response.status_code == 200

    response = client.get(f"/carts/{cart_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(cart_id)

    assert [
        (
            item["variant_id"],
            item["quantity"],
            item["line_total_cents"],
        )
        for item in body["items"]
    ] == [
        (shirt_variant_id, 2, 5998),
        (tote_variant_id, 3, 5997),
    ]
    assert body["subtotal_cents"] == 11995

    other_response = client.get(f"/carts/{other_cart_id}")

    assert other_response.status_code == 200
    other_body = other_response.json()
    assert other_body["id"] == str(other_cart_id)
    assert len(other_body["items"]) == 1
    assert other_body["items"][0]["variant_id"] == shirt_variant_id
    assert other_body["items"][0]["quantity"] == 1
    assert other_body["subtotal_cents"] == 2999