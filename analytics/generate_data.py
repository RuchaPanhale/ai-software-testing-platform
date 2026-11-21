"""Generate Cartiva's synthetic shop dataset for SQL and Tableau analysis.

Run from the repository root:
    python -m analytics.generate_data

Writes CSV files to analytics/data/. The same seed always produces exactly
the same data. Every behavioral assumption is a named constant in the
ASSUMPTIONS section below and is documented in docs/data-assumptions.md.
Change a number there, re-run, and the dataset changes accordingly.

The data is SYNTHETIC. Patterns in it exist because these assumptions put
them there; they are not real customer behavior.
"""

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from analytics.pricing import sale_discount, shipping_cents, welcome10_discount
from cartiva.catalog_data import CATALOG

OUTPUT_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# ASSUMPTIONS (see docs/data-assumptions.md for the reasoning behind each)
# ---------------------------------------------------------------------------
DEFAULT_SEED = 2025
DEFAULT_NUM_CUSTOMERS = 8000
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

# Relative traffic by month: quieter after the holidays, busy Nov-Dec.
MONTH_WEIGHTS = {1: 0.80, 2: 0.75, 3: 0.85, 4: 0.90, 5: 0.95, 6: 1.00,
                 7: 1.05, 8: 1.00, 9: 0.95, 10: 1.00, 11: 1.35, 12: 1.60}


@dataclass(frozen=True)
class Sale:
    code: str
    name: str
    percent_off: int
    starts_on: date
    ends_on: date  # inclusive


# Automatic sitewide sales. During a sale, the sale discount applies and
# WELCOME10 is not accepted (one discount per order, CART-004).
SALES = [
    Sale("SUMMER2024", "Summer Sale 2024", 15, date(2024, 7, 8), date(2024, 7, 14)),
    Sale("BLACKFRIDAY2024", "Black Friday Weekend 2024", 25,
         date(2024, 11, 29), date(2024, 12, 2)),
    Sale("SUMMER2025", "Summer Sale 2025", 15, date(2025, 7, 7), date(2025, 7, 13)),
    Sale("BLACKFRIDAY2025", "Black Friday Weekend 2025", 25,
         date(2025, 11, 28), date(2025, 12, 1)),
]
SALE_TRAFFIC_MULTIPLIER = 2.5       # more visits on sale days
SALE_ADD_TO_CART_MULTIPLIER = 1.30  # shoppers add more during a sale
SALE_PURCHASE_MULTIPLIER = 1.15     # and are more likely to finish

ACQUISITION_CHANNELS = {"organic_search": 0.35, "paid_social": 0.25,
                        "email": 0.15, "referral": 0.10, "direct": 0.15}
RETURN_VISIT_CHANNELS = {"email": 0.35, "direct": 0.35,
                         "organic_search": 0.20, "paid_social": 0.10}
DEVICES = {"mobile": 0.60, "desktop": 0.35, "tablet": 0.05}
STATES = {"CA": 0.16, "NY": 0.12, "TX": 0.11, "FL": 0.09, "IL": 0.06,
          "WA": 0.05, "MA": 0.05, "NJ": 0.05, "PA": 0.05, "GA": 0.05,
          "CO": 0.04, "AZ": 0.04, "OR": 0.03, "NC": 0.05, "OH": 0.05}

# How often each category is browsed, relative to 1.0.
CATEGORY_POPULARITY = {"Tops": 1.4, "Shirts": 1.2, "Jeans": 1.2,
                       "Dresses": 1.0, "Shoes": 1.0, "Accessories": 1.1,
                       "Knitwear": 0.8, "Outerwear": 0.7}

P_RETURN_VISIT = 0.70               # chance of each additional session
RETURN_WINDOW_DAYS = 90             # a return visit is within 90 days
VIEWS_PER_SESSION = {1: 0.20, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.12, 6: 0.08}
P_ADD_TO_CART = 0.12                # per product viewed
P_QUANTITY_TWO = 0.12               # otherwise quantity is 1
P_CHECKOUT_GIVEN_CART = 0.55
P_PURCHASE_GIVEN_CHECKOUT = 0.65

# Big-ticket hesitation: applied using the priciest item's category.
CATEGORY_PURCHASE_MULTIPLIER = {"Outerwear": 0.80, "Shoes": 0.90,
                                "Accessories": 1.10}
DEVICE_PURCHASE_MULTIPLIER = {"mobile": 0.85, "desktop": 1.10, "tablet": 1.00}

# WELCOME10 experiment: half of new customers are offered the code for
# their first order. BUILT-IN EFFECT (disclosed): treatment customers are
# 15% more likely to complete checkout before their first order.
TREATMENT_SHARE = 0.50
TREATMENT_FIRST_ORDER_PURCHASE_MULTIPLIER = 1.15
P_USE_CODE_IF_ELIGIBLE = 0.85

# Busier evenings: weights for the hour a session starts.
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 5, 6,
                7, 7, 6, 6, 6, 7, 8, 10, 11, 10, 7, 3]
# ---------------------------------------------------------------------------

PRODUCT_COLUMNS = ["product_id", "name", "category", "description"]
VARIANT_COLUMNS = ["variant_id", "product_id", "size", "color", "price_cents"]
PROMOTION_COLUMNS = ["promotion_code", "name", "promotion_type", "percent_off",
                     "min_subtotal_cents", "max_discount_cents",
                     "starts_on", "ends_on"]
CUSTOMER_COLUMNS = ["customer_id", "signup_date", "state",
                    "acquisition_channel", "experiment_group"]
SESSION_COLUMNS = ["session_id", "customer_id", "started_at", "device",
                   "traffic_channel"]
EVENT_COLUMNS = ["event_id", "session_id", "customer_id", "event_type",
                 "occurred_at", "product_id", "variant_id", "order_id"]
ORDER_COLUMNS = ["order_id", "customer_id", "session_id", "ordered_at",
                 "promotion_code", "subtotal_cents", "discount_cents",
                 "shipping_cents", "total_cents"]
ORDER_ITEM_COLUMNS = ["order_item_id", "order_id", "product_id", "variant_id",
                      "product_name", "category", "size", "color", "quantity",
                      "unit_price_cents", "line_total_cents"]


def pick(rng: random.Random, weights: dict):
    """Pick one key from a {value: weight} dictionary."""
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def sale_on(day: date) -> Sale | None:
    for sale in SALES:
        if sale.starts_on <= day <= sale.ends_on:
            return sale
    return None


def build_catalog() -> tuple[list[dict], list[dict]]:
    """Number products and variants 1..N in catalog order."""
    products, variants = [], []
    for product_id, item in enumerate(CATALOG, start=1):
        products.append({"product_id": product_id, "name": item["name"],
                         "category": item["category"],
                         "description": item["description"]})
        for size, color, price_cents, stock in item["variants"]:
            variants.append({"variant_id": len(variants) + 1,
                             "product_id": product_id, "size": size,
                             "color": color, "price_cents": price_cents,
                             "in_stock": stock > 0})
    return products, variants


def build_promotions() -> list[dict]:
    rows = [{"promotion_code": "WELCOME10", "name": "Welcome offer",
             "promotion_type": "code", "percent_off": 10,
             "min_subtotal_cents": 5000, "max_discount_cents": 2000,
             "starts_on": START_DATE, "ends_on": END_DATE}]
    for sale in SALES:
        rows.append({"promotion_code": sale.code, "name": sale.name,
                     "promotion_type": "automatic",
                     "percent_off": sale.percent_off,
                     "min_subtotal_cents": 0, "max_discount_cents": "",
                     "starts_on": sale.starts_on, "ends_on": sale.ends_on})
    return rows


def generate(seed: int = DEFAULT_SEED,
             num_customers: int = DEFAULT_NUM_CUSTOMERS) -> dict[str, list[dict]]:
    """Return every table as a list of row dictionaries."""
    rng = random.Random(seed)
    products, variants = build_catalog()
    product_by_id = {p["product_id"]: p for p in products}
    variants_by_product: dict[int, list[dict]] = {}
    for v in variants:
        if v["in_stock"]:  # sold-out variants can be viewed, never added
            variants_by_product.setdefault(v["product_id"], []).append(v)
    product_weights = [CATEGORY_POPULARITY[p["category"]] for p in products]

    days = [START_DATE + timedelta(n)
            for n in range((END_DATE - START_DATE).days + 1)]
    # Extend the calendar past END_DATE only for picking return visits, so
    # late-year customers aren't squeezed into the last days of December.
    calendar = days + [END_DATE + timedelta(n)
                       for n in range(1, RETURN_WINDOW_DAYS + 1)]
    day_weights = [MONTH_WEIGHTS[d.month]
                   * (SALE_TRAFFIC_MULTIPLIER if sale_on(d) else 1.0)
                   for d in calendar]

    customers, sessions, events, orders, order_items = [], [], [], [], []

    def add_event(session_id, customer_id, event_type, when,
                  product_id="", variant_id="", order_id=""):
        events.append({"event_id": len(events) + 1, "session_id": session_id,
                       "customer_id": customer_id, "event_type": event_type,
                       "occurred_at": when, "product_id": product_id,
                       "variant_id": variant_id, "order_id": order_id})

    for customer_id in range(1, num_customers + 1):
        signup_index = rng.choices(range(len(days)),
                                   weights=day_weights[:len(days)])[0]
        group = "treatment" if rng.random() < TREATMENT_SHARE else "control"
        acquisition = pick(rng, ACQUISITION_CHANNELS)
        customers.append({"customer_id": customer_id,
                          "signup_date": days[signup_index],
                          "state": pick(rng, STATES),
                          "acquisition_channel": acquisition,
                          "experiment_group": group})

        # First visit is the signup day. Each return visit falls within
        # RETURN_WINDOW_DAYS after the previous one; busier days are likelier.
        visit_indexes = [signup_index]
        while rng.random() < P_RETURN_VISIT:
            start = visit_indexes[-1] + 1
            stop = start + RETURN_WINDOW_DAYS
            visit = rng.choices(range(start, stop),
                                weights=day_weights[start:stop])[0]
            if visit >= len(days):
                break  # this visit would fall after the data ends
            visit_indexes.append(visit)

        has_ordered = False
        for visit_number, day_index in enumerate(visit_indexes):
            day = days[day_index]
            sale = sale_on(day)
            device = pick(rng, DEVICES)
            channel = (acquisition if visit_number == 0
                       else pick(rng, RETURN_VISIT_CHANNELS))
            hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
            clock = datetime.combine(day, time(hour, rng.randrange(60),
                                               rng.randrange(60)))
            session_id = len(sessions) + 1
            sessions.append({"session_id": session_id,
                             "customer_id": customer_id, "started_at": clock,
                             "device": device, "traffic_channel": channel})

            # Browse, and maybe add items to the cart.
            cart: list[tuple[dict, int]] = []
            p_add = min(1.0, P_ADD_TO_CART
                        * (SALE_ADD_TO_CART_MULTIPLIER if sale else 1.0))
            for _ in range(pick(rng, VIEWS_PER_SESSION)):
                product = rng.choices(products, weights=product_weights)[0]
                clock += timedelta(seconds=rng.randint(20, 180))
                add_event(session_id, customer_id, "product_view", clock,
                          product_id=product["product_id"])
                options = variants_by_product.get(product["product_id"], [])
                if options and rng.random() < p_add:
                    variant = rng.choice(options)
                    quantity = 2 if rng.random() < P_QUANTITY_TWO else 1
                    cart.append((variant, quantity))
                    clock += timedelta(seconds=rng.randint(10, 60))
                    add_event(session_id, customer_id, "add_to_cart", clock,
                              product_id=product["product_id"],
                              variant_id=variant["variant_id"])

            if not cart or rng.random() >= P_CHECKOUT_GIVEN_CART:
                continue  # left without starting checkout
            clock += timedelta(seconds=rng.randint(30, 120))
            add_event(session_id, customer_id, "checkout_start", clock)

            # Will they complete the purchase?
            priciest = max(cart, key=lambda c: c[0]["price_cents"])[0]
            category = product_by_id[priciest["product_id"]]["category"]
            p_buy = (P_PURCHASE_GIVEN_CHECKOUT
                     * CATEGORY_PURCHASE_MULTIPLIER.get(category, 1.0)
                     * DEVICE_PURCHASE_MULTIPLIER[device]
                     * (SALE_PURCHASE_MULTIPLIER if sale else 1.0))
            if group == "treatment" and not has_ordered and not sale:
                p_buy *= TREATMENT_FIRST_ORDER_PURCHASE_MULTIPLIER
            if rng.random() >= min(1.0, p_buy):
                continue  # abandoned at checkout

            # Price the order with the CART-004..006 rules.
            order_id = len(orders) + 1
            subtotal = sum(v["price_cents"] * q for v, q in cart)
            code, discount = "", 0
            if sale:
                code, discount = sale.code, sale_discount(subtotal,
                                                          sale.percent_off)
            elif (group == "treatment" and not has_ordered
                  and welcome10_discount(subtotal) > 0
                  and rng.random() < P_USE_CODE_IF_ELIGIBLE):
                code, discount = "WELCOME10", welcome10_discount(subtotal)
            shipping = shipping_cents(subtotal, discount)
            clock += timedelta(seconds=rng.randint(30, 180))
            orders.append({"order_id": order_id, "customer_id": customer_id,
                           "session_id": session_id, "ordered_at": clock,
                           "promotion_code": code, "subtotal_cents": subtotal,
                           "discount_cents": discount,
                           "shipping_cents": shipping,
                           "total_cents": subtotal - discount + shipping})
            for variant, quantity in cart:
                product = product_by_id[variant["product_id"]]
                order_items.append({
                    "order_item_id": len(order_items) + 1,
                    "order_id": order_id, "product_id": product["product_id"],
                    "variant_id": variant["variant_id"],
                    "product_name": product["name"],
                    "category": product["category"], "size": variant["size"],
                    "color": variant["color"], "quantity": quantity,
                    "unit_price_cents": variant["price_cents"],
                    "line_total_cents": variant["price_cents"] * quantity})
            add_event(session_id, customer_id, "purchase", clock,
                      order_id=order_id)
            has_ordered = True

    customers, sessions, events, orders, order_items = renumber_by_time(
        customers, sessions, events, orders, order_items)
    return {"products": products,
            "product_variants": [{k: v[k] for k in VARIANT_COLUMNS}
                                 for v in variants],
            "promotions": build_promotions(),
            "customers": customers, "sessions": sessions, "events": events,
            "orders": orders, "order_items": order_items}


def renumber_by_time(customers, sessions, events, orders, order_items):
    """Give IDs in time order, as a real system would assign them.

    Rows are generated customer by customer, so raw IDs are not
    chronological. Sort each table by time and renumber, updating every
    reference so the joins stay correct.
    """
    customers = sorted(customers, key=lambda r: (r["signup_date"],
                                                 r["customer_id"]))
    customer_map = {r["customer_id"]: n for n, r in enumerate(customers, 1)}
    sessions = sorted(sessions, key=lambda r: (r["started_at"],
                                               r["session_id"]))
    session_map = {r["session_id"]: n for n, r in enumerate(sessions, 1)}
    orders = sorted(orders, key=lambda r: (r["ordered_at"], r["order_id"]))
    order_map = {r["order_id"]: n for n, r in enumerate(orders, 1)}
    events = sorted(events, key=lambda r: (r["occurred_at"], r["event_id"]))

    for row in customers:
        row["customer_id"] = customer_map[row["customer_id"]]
    for row in sessions:
        row["session_id"] = session_map[row["session_id"]]
        row["customer_id"] = customer_map[row["customer_id"]]
    for row in orders:
        row["order_id"] = order_map[row["order_id"]]
        row["session_id"] = session_map[row["session_id"]]
        row["customer_id"] = customer_map[row["customer_id"]]
    for n, row in enumerate(events, 1):
        row["event_id"] = n
        row["session_id"] = session_map[row["session_id"]]
        row["customer_id"] = customer_map[row["customer_id"]]
        if row["order_id"] != "":
            row["order_id"] = order_map[row["order_id"]]
    for row in order_items:
        row["order_id"] = order_map[row["order_id"]]
    order_items = sorted(order_items, key=lambda r: (r["order_id"],
                                                     r["order_item_id"]))
    for n, row in enumerate(order_items, 1):
        row["order_item_id"] = n
    return customers, sessions, events, orders, order_items


COLUMNS = {"products": PRODUCT_COLUMNS, "product_variants": VARIANT_COLUMNS,
           "promotions": PROMOTION_COLUMNS, "customers": CUSTOMER_COLUMNS,
           "sessions": SESSION_COLUMNS, "events": EVENT_COLUMNS,
           "orders": ORDER_COLUMNS, "order_items": ORDER_ITEM_COLUMNS}


def check(tables: dict[str, list[dict]]) -> None:
    """Fail loudly if the generated data breaks its own rules."""
    items_by_order: dict[int, int] = {}
    for item in tables["order_items"]:
        assert item["line_total_cents"] == (item["unit_price_cents"]
                                            * item["quantity"])
        items_by_order[item["order_id"]] = (items_by_order.get(item["order_id"], 0)
                                            + item["line_total_cents"])
    for order in tables["orders"]:
        assert order["subtotal_cents"] == items_by_order[order["order_id"]]
        assert order["total_cents"] == (order["subtotal_cents"]
                                        - order["discount_cents"]
                                        + order["shipping_cents"])
    purchases = [e for e in tables["events"] if e["event_type"] == "purchase"]
    assert len(purchases) == len(tables["orders"])


def write_csvs(tables: dict[str, list[dict]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        with open(output_dir / f"{name}.csv", "w", newline="",
                  encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS[name])
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--customers", type=int,
                        default=DEFAULT_NUM_CUSTOMERS)
    args = parser.parse_args()

    tables = generate(args.seed, args.customers)
    check(tables)
    write_csvs(tables, OUTPUT_DIR)
    print(f"Seed {args.seed}: wrote {len(tables)} tables to {OUTPUT_DIR}")
    for name, rows in tables.items():
        print(f"  {name:<17} {len(rows):>7,} rows")


if __name__ == "__main__":
    main()
