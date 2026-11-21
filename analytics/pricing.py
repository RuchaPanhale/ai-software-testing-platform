"""Order pricing rules from docs/cartiva-requirements.md (CART-004 to CART-006).

All amounts are integer cents. These functions are pure: same input,
same output, no database access.
"""

WELCOME10_PERCENT = 10
WELCOME10_MIN_SUBTOTAL_CENTS = 5000   # $50.00, inclusive (CART-004)
WELCOME10_MAX_DISCOUNT_CENTS = 2000   # $20.00 cap (CART-004)
SHIPPING_CENTS = 599                  # $5.99 standard shipping (CART-005)
FREE_SHIPPING_ABOVE_CENTS = 10000     # free only when strictly above $100.00


def percent_of(amount_cents: int, percent: int) -> int:
    """Return percent of an amount, rounded to the nearest cent, halves up.

    Integer arithmetic avoids floating-point errors:
    5005 cents * 10% = 500.5 cents -> 501 cents.
    """
    return (amount_cents * percent + 50) // 100


def welcome10_discount(subtotal_cents: int) -> int:
    """WELCOME10: 10% off, minimum $50.00 subtotal, capped at $20.00."""
    if subtotal_cents < WELCOME10_MIN_SUBTOTAL_CENTS:
        return 0
    return min(percent_of(subtotal_cents, WELCOME10_PERCENT),
               WELCOME10_MAX_DISCOUNT_CENTS)


def sale_discount(subtotal_cents: int, percent: int) -> int:
    """Sitewide automatic sale: a flat percentage, no minimum, no cap."""
    return percent_of(subtotal_cents, percent)


def shipping_cents(subtotal_cents: int, discount_cents: int) -> int:
    """Shipping is free only when the total AFTER discounts is above $100.00."""
    if subtotal_cents == 0:
        return 0
    after_discount = subtotal_cents - discount_cents
    return 0 if after_discount > FREE_SHIPPING_ABOVE_CENTS else SHIPPING_CENTS


def final_total_cents(subtotal_cents: int, discount_cents: int) -> int:
    """Final total = subtotal - discount + shipping (CART-006)."""
    return (subtotal_cents - discount_cents
            + shipping_cents(subtotal_cents, discount_cents))
