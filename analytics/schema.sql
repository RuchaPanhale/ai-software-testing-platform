-- Cartiva analytics schema: the synthetic shop dataset for SQL analysis.
--
-- Kept in its own schema, separate from the app's tables in "public".
-- Safe to re-run: it drops and recreates only the analytics schema.
-- Money is integer cents. Timestamps are UTC, without time zone.

DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

CREATE TABLE analytics.products (
    product_id   integer PRIMARY KEY,
    name         text    NOT NULL,
    category     text    NOT NULL,
    description  text    NOT NULL
);

CREATE TABLE analytics.product_variants (
    variant_id   integer PRIMARY KEY,
    product_id   integer NOT NULL REFERENCES analytics.products,
    size         text    NOT NULL,
    color        text    NOT NULL,
    price_cents  integer NOT NULL CHECK (price_cents >= 0)
);

CREATE TABLE analytics.promotions (
    promotion_code      text    PRIMARY KEY,
    name                text    NOT NULL,
    promotion_type      text    NOT NULL
                        CHECK (promotion_type IN ('code', 'automatic')),
    percent_off         integer NOT NULL CHECK (percent_off BETWEEN 1 AND 100),
    min_subtotal_cents  integer NOT NULL CHECK (min_subtotal_cents >= 0),
    max_discount_cents  integer CHECK (max_discount_cents >= 0),  -- NULL = no cap
    starts_on           date    NOT NULL,
    ends_on             date    NOT NULL,
    CHECK (ends_on >= starts_on)
);

CREATE TABLE analytics.customers (
    customer_id          integer PRIMARY KEY,
    signup_date          date    NOT NULL,
    state                text    NOT NULL,
    acquisition_channel  text    NOT NULL,
    experiment_group     text    NOT NULL
                         CHECK (experiment_group IN ('control', 'treatment'))
);

CREATE TABLE analytics.sessions (
    session_id       integer   PRIMARY KEY,
    customer_id      integer   NOT NULL REFERENCES analytics.customers,
    started_at       timestamp NOT NULL,
    device           text      NOT NULL,
    traffic_channel  text      NOT NULL
);

CREATE TABLE analytics.orders (
    order_id        integer   PRIMARY KEY,
    customer_id     integer   NOT NULL REFERENCES analytics.customers,
    session_id      integer   NOT NULL UNIQUE REFERENCES analytics.sessions,
    ordered_at      timestamp NOT NULL,
    promotion_code  text      REFERENCES analytics.promotions,  -- NULL = none
    subtotal_cents  integer   NOT NULL CHECK (subtotal_cents > 0),
    discount_cents  integer   NOT NULL CHECK (discount_cents >= 0),
    shipping_cents  integer   NOT NULL CHECK (shipping_cents >= 0),
    total_cents     integer   NOT NULL,
    CHECK (discount_cents <= subtotal_cents),
    CHECK (total_cents = subtotal_cents - discount_cents + shipping_cents)
);

CREATE TABLE analytics.order_items (
    order_item_id     integer PRIMARY KEY,
    order_id          integer NOT NULL REFERENCES analytics.orders,
    product_id        integer NOT NULL REFERENCES analytics.products,
    variant_id        integer NOT NULL REFERENCES analytics.product_variants,
    product_name      text    NOT NULL,  -- snapshot at purchase time
    category          text    NOT NULL,
    size              text    NOT NULL,
    color             text    NOT NULL,
    quantity          integer NOT NULL CHECK (quantity > 0),
    unit_price_cents  integer NOT NULL CHECK (unit_price_cents >= 0),
    line_total_cents  integer NOT NULL,
    CHECK (line_total_cents = unit_price_cents * quantity)
);

CREATE TABLE analytics.events (
    event_id     integer   PRIMARY KEY,
    session_id   integer   NOT NULL REFERENCES analytics.sessions,
    customer_id  integer   NOT NULL REFERENCES analytics.customers,
    event_type   text      NOT NULL CHECK (event_type IN
                 ('product_view', 'add_to_cart', 'checkout_start', 'purchase')),
    occurred_at  timestamp NOT NULL,
    product_id   integer   REFERENCES analytics.products,          -- views, adds
    variant_id   integer   REFERENCES analytics.product_variants,  -- adds only
    order_id     integer   REFERENCES analytics.orders             -- purchases only
);

-- Indexes for the joins and date filters analysis queries use most.
CREATE INDEX ON analytics.sessions (customer_id);
CREATE INDEX ON analytics.sessions (started_at);
CREATE INDEX ON analytics.orders (customer_id);
CREATE INDEX ON analytics.orders (ordered_at);
CREATE INDEX ON analytics.order_items (order_id);
CREATE INDEX ON analytics.events (session_id);
CREATE INDEX ON analytics.events (event_type, occurred_at);
