"""Shopping cart API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from cartiva.backend.database import get_session
from cartiva.backend.models import Cart
from cartiva.backend.schemas import CartCreated


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