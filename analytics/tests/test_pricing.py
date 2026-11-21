"""Pricing rules, checked against the acceptance examples in
docs/cartiva-requirements.md (CART-004, CART-005, CART-006)."""

import pytest

from analytics.pricing import (
    final_total_cents,
    percent_of,
    sale_discount,
    shipping_cents,
    welcome10_discount,
)


@pytest.mark.parametrize(
    ("subtotal_cents", "expected_discount_cents", "acceptance_id"),
    [
        (4999, 0, "AC-004-02"),    # $49.99 is below the $50.00 minimum
        (5000, 500, "AC-004-03"),  # exactly $50.00 qualifies: $5.00 off
        (25000, 2000, "AC-004-04"),  # 10% of $250 is $25, capped at $20
        (5005, 501, "AC-004-05"),  # $5.005 rounds half up to $5.01
    ],
)
def test_welcome10_discount(subtotal_cents, expected_discount_cents,
                            acceptance_id):
    assert welcome10_discount(subtotal_cents) == expected_discount_cents


@pytest.mark.parametrize(
    ("subtotal_cents", "discount_cents", "expected_shipping_cents",
     "acceptance_id"),
    [
        (9999, 0, 599, "AC-005-01"),    # $99.99 pays shipping
        (10000, 0, 599, "AC-005-02"),   # exactly $100.00 still pays
        (10001, 0, 0, "AC-005-03"),     # $100.01 ships free
        (11000, 1100, 599, "AC-005-04"),  # $110 - $11 = $99.00, pays
    ],
)
def test_shipping(subtotal_cents, discount_cents, expected_shipping_cents,
                  acceptance_id):
    assert shipping_cents(subtotal_cents, discount_cents) == (
        expected_shipping_cents
    )


def test_final_total_ac_006_01():
    # $110.00 - $11.00 discount + $5.99 shipping = $104.99
    assert final_total_cents(11000, 1100) == 10499


def test_empty_cart_has_no_shipping():
    assert shipping_cents(0, 0) == 0


def test_percent_rounds_half_up():
    assert percent_of(5005, 10) == 501   # 500.5 -> 501
    assert percent_of(5004, 10) == 500   # 500.4 -> 500


def test_sale_discount_has_no_cap():
    assert sale_discount(100000, 25) == 25000
