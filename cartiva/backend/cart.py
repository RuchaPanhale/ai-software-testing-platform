"""Shopping cart API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from cartiva.backend.database import get_session
from cartiva.backend.models import Cart, CartItem, ProductVariant
from cartiva.backend.schemas import CartCreated, CartItemAdd, CartItemRead


router = APIRouter(prefix="/carts", tags=["Cart"])

SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=CartCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_cart(session: SessionDependency) -> CartCreated:
    """Create and persist an empty shopping cart."""

    cart = Cart()
    session.add(cart)
    session.commit()
    session.refresh(cart)

    return CartCreated(id=cart.id)


@router.post("/{cart_id}/items", response_model=CartItemRead)
def add_cart_item(
    cart_id: UUID,
    payload: CartItemAdd,
    session: SessionDependency,
) -> CartItemRead:
    """Add a variant or increase its existing quantity."""

    #cart = session.get(Cart, cart_id)

    # Serialize changes to this cart until the transaction finishes.
    cart = session.exec(
        select(Cart)
        .where(Cart.id == cart_id)
        .with_for_update()
    ).first()

    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    variant = session.get(ProductVariant, payload.variant_id)

    if variant is None:
        raise HTTPException(status_code=404, detail="Product variant not found")

    item = session.exec(
        select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.variant_id == payload.variant_id,
        )
    ).first()

    existing_quantity = item.quantity if item is not None else 0
    new_quantity = existing_quantity + payload.quantity

    if new_quantity > variant.stock_quantity:
        raise HTTPException(
            status_code=409,
            detail="Requested quantity exceeds available stock",
        )

    if item is None:
        item = CartItem(
            cart_id=cart_id,
            variant_id=payload.variant_id,
            quantity=new_quantity,
        )
    else:
        item.quantity = new_quantity

    session.add(item)
    session.commit()
    session.refresh(item)

    return CartItemRead.model_validate(item)