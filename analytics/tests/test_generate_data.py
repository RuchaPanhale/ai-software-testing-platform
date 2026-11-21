"""The synthetic dataset must be reproducible and follow its own rules."""

from datetime import date

import pytest

from analytics.generate_data import SALES, check, generate


@pytest.fixture(scope="module")
def tables():
    # A smaller run keeps the tests fast; the rules are the same.
    return generate(seed=7, num_customers=600)


def test_same_seed_gives_identical_data(tables):
    assert generate(seed=7, num_customers=600) == tables


def test_different_seed_gives_different_data(tables):
    assert generate(seed=8, num_customers=600)["orders"] != tables["orders"]


def test_internal_checks_pass(tables):
    check(tables)  # raises AssertionError on any broken total or count


def test_every_reference_points_to_an_existing_row(tables):
    customer_ids = {c["customer_id"] for c in tables["customers"]}
    session_ids = {s["session_id"] for s in tables["sessions"]}
    order_ids = {o["order_id"] for o in tables["orders"]}
    variant_ids = {v["variant_id"] for v in tables["product_variants"]}

    assert {s["customer_id"] for s in tables["sessions"]} <= customer_ids
    assert {e["session_id"] for e in tables["events"]} <= session_ids
    assert {o["session_id"] for o in tables["orders"]} <= session_ids
    assert {i["order_id"] for i in tables["order_items"]} == order_ids
    assert {i["variant_id"] for i in tables["order_items"]} <= variant_ids


def test_ids_follow_time_order(tables):
    times = [o["ordered_at"] for o in tables["orders"]]
    assert times == sorted(times)


def test_welcome10_only_for_treatment_first_orders_of_at_least_50(tables):
    group = {c["customer_id"]: c["experiment_group"]
             for c in tables["customers"]}
    first_order = {}
    for order in tables["orders"]:  # already in time order
        first_order.setdefault(order["customer_id"], order["order_id"])

    for order in tables["orders"]:
        if order["promotion_code"] == "WELCOME10":
            assert group[order["customer_id"]] == "treatment"
            assert first_order[order["customer_id"]] == order["order_id"]
            assert order["subtotal_cents"] >= 5000
            assert order["discount_cents"] <= 2000


def test_sale_codes_only_on_sale_days(tables):
    sale_days = {sale.code: (sale.starts_on, sale.ends_on) for sale in SALES}
    for order in tables["orders"]:
        code = order["promotion_code"]
        if code in sale_days:
            starts_on, ends_on = sale_days[code]
            assert starts_on <= order["ordered_at"].date() <= ends_on


def test_no_activity_outside_the_data_period(tables):
    for session in tables["sessions"]:
        assert date(2024, 1, 1) <= session["started_at"].date() <= date(
            2025, 12, 31)
