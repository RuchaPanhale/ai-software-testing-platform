"""Cart API tests using an isolated in-memory database."""

from uuid import UUID

from sqlmodel import Session, select

from cartiva.backend.models import Cart, CartItem


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