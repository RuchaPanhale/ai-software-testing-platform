# Cartiva: E-commerce Analytics & AI Test-Evaluation Project

[![Backend CI](https://github.com/RuchaPanhale/ai-software-testing-platform/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/RuchaPanhale/ai-software-testing-platform/actions/workflows/tests.yml)

> **I measured an e-commerce product, and I measured an AI that tests it.**

Cartiva is a fictional fashion store. I wrote its business rules
(pricing, discounts, shipping, stock, search) as numbered requirements, built
a tested backend that enforces them, and use it as a controlled environment
for two kinds of analysis:

1. **Business analytics:** how shoppers move from browsing to buying, and
   whether a discount code actually changes behavior.
2. **AI evaluation:** how good LLM-generated test cases really are, measured
   against human judgment and against bugs I plant on purpose.

A personal portfolio project by **Rucha Panhale** (MS Computer Science, AI track),
built to demonstrate data modeling, SQL, experiment design, and AI-evaluation skills.

[LinkedIn](https://www.linkedin.com/in/rucha-panhale/)

---

## Project status

| Area | Status |
|---|---|
| Business rules written as testable requirements (CART-001 to CART-013) | ✅ Done |
| Backend: catalog, search, filters, cart, order tables | ✅ Done |
| Automated tests (79 test cases) + CI on every push | ✅ Done |
| Controlled regression experiment (1 planted defect) | ✅ Done |
| Pricing rules: WELCOME10 discount, shipping, totals (tested against the acceptance examples) | ✅ Done |
| Synthetic shop dataset: 2 years, 8,000 customers, ~80K events | ✅ Done |
| Storefront page (browse, filter, search, add to bag) | ✅ Done |
| SQL analysis + findings memo | 🔄 In progress |
| Tableau Public dashboard | 🔄 In progress |
| WELCOME10 A/B significance test | 📋 Planned |
| Mutation suite + LLM test-proposal evaluation | 📋 Planned (later phase) |

Only items marked ✅ are built and verified. Everything else is a plan, not a result.

---

## How it fits together

```mermaid
flowchart LR
    R["📄 Requirements<br/>CART-001 to CART-013<br/>business rules + examples"]

    subgraph APP["Cartiva app ✅"]
        SHOP["Storefront"] --> API["FastAPI backend"] --> DB[("PostgreSQL")]
    end

    subgraph BIZ["Business analytics"]
        GEN["Synthetic shop data ✅<br/>sessions, events, orders"] --> SQL["SQL analysis 🔄<br/>funnel, AOV, A/B test"]
    end

    subgraph EVAL["AI evaluation 📋"]
        LLM["LLM proposes tests<br/>as structured JSON"] --> HUM["Human review<br/>+ rubric scoring"]
        HUM --> RUN["Trusted test runner"]
    end

    R --> API
    R --> LLM
    DB --> GEN
    RUN --> API
    SQL --> DASH["📊 Tableau dashboard 🔄"]
    RUN --> DASH
```

The **requirements document** is the anchor. The app enforces it, the tests
check it, and the AI's proposals are judged against it.

---

## Questions this project answers

**Business (data analyst)** — 🔄 in progress: SQL queries and a Tableau dashboard ([see below](#7-analysis-in-progress))
- Where do shoppers drop off between viewing a product, adding to cart, and ordering?
- Which categories have the highest cart-abandonment rate?
- What is the average order value, and how does it vary by category?
- **Does the WELCOME10 code increase conversion?** Run as an A/B test with a
  significance test, not eyeballed from a chart.

**AI evaluation** — 📋 planned (later phase)
- What share of LLM-proposed test cases are valid, relevant, correct, and in scope?
- Do two human raters agree on what a "good" proposal is (Cohen's kappa)?
- Does an LLM judge agree with human labels? Where does it disagree?
- **Do AI-proposed tests catch planted bugs** as well as hand-written tests?

---

## What's built

### 1. Business rules as testable requirements

[`docs/cartiva-requirements.md`](docs/cartiva-requirements.md) defines 13
requirements with acceptance examples, including the edge cases:

| Rule | Example |
|---|---|
| WELCOME10: 10% off, minimum $50.00, capped at $20.00 | A $49.99 cart is ineligible; $250.00 gets the capped $20.00 off |
| Rounding: half-cents round up | $50.05 gets $5.01 off |
| Free shipping only **above** $100.00 after discounts | Exactly $100.00 still pays $5.99 |
| Search must not mix colors from different variants | "green black shirt" doesn't match a shirt sold separately in green and in black |

These rules are the ground truth for the tests and for the AI evaluation.

### 2. A data model built for trustworthy data

```mermaid
erDiagram
    PRODUCTS ||--o{ PRODUCT_VARIANTS : "has"
    CARTS ||--o{ CART_ITEMS : "contains"
    PRODUCT_VARIANTS ||--o{ CART_ITEMS : "added as"
    CARTS ||--o| ORDERS : "checked out as"
    ORDERS ||--o{ ORDER_ITEMS : "contains"
    PRODUCT_VARIANTS ||--o{ ORDER_ITEMS : "purchased as"

    PRODUCTS {
        int id PK
        string name
        string category
        string description
    }
    PRODUCT_VARIANTS {
        int id PK
        int product_id FK
        string size
        string color
        int price_cents
        int stock_quantity
    }
    CARTS {
        uuid id PK
    }
    CART_ITEMS {
        int id PK
        uuid cart_id FK
        int variant_id FK
        int quantity
    }
    ORDERS {
        uuid id PK
        uuid cart_id FK "unique: one order per cart"
        datetime created_at "UTC"
        int subtotal_cents
    }
    ORDER_ITEMS {
        int id PK
        uuid order_id FK
        int variant_id FK
        string product_name "snapshot"
        int quantity
        int unit_price_cents "price at purchase"
        int line_total_cents
    }
```

Design choices that matter for analysis:
- **Money is stored as integer cents** (e.g. $19.99 = 1999), so totals never
  suffer floating-point rounding errors.
- **Order items keep a snapshot** of product name, size, color and price at the
  time of purchase. Later catalog price changes don't rewrite sales history.
- **The database rejects bad data itself**, through check constraints: no
  negative prices or stock, no zero quantities, no blank names, and
  `line_total = unit_price × quantity` is enforced on every order line.
- **Prices are calculated on the server**, so a client can't send its own price.
- **Two database roles:** an owner role runs migrations, and the app connects
  through a restricted role with only the permissions it needs.

### 3. Automated tests and CI

- **59 API test cases** cover catalog, search, filters, cart behavior (stock
  limits, invalid quantities, missing records, price tampering, carts that are
  already checked out) and the storefront page.
- **20 data tests** check the pricing rules against the acceptance examples in
  the requirements, and check that the dataset is reproducible and internally
  consistent.
- Each test gets a **fresh, isolated database**, so tests never depend on
  each other or on local data.
- **GitHub Actions runs on every push and pull request:** it applies all
  database migrations to a fresh PostgreSQL instance, checks that the models
  and the database schema haven't drifted apart, runs the tests, and saves a
  JUnit XML results file.

### 4. Controlled regression experiment

To check that the tests catch real bugs, I ran the same suite against two
copies of the code:

```mermaid
flowchart LR
    BASE["Baseline code"] --> T1["Same 55 tests"] --> R1["✅ 55 passed, 0 failed"]
    BUG["Copy with 1 planted bug:<br/>subtotal adds unit prices,<br/>ignoring quantity"] --> T2["Same 55 tests"] --> R2["❌ 48 passed, 7 failed"]
```

| Version | Passed | Failed |
|---|---:|---:|
| Baseline (commit `ef3acb4`) | 55 | 0 |
| Planted subtotal bug | 48 | 7 |

**Finding:** 7 tests caught the bug. For example, a two-item cart that should
total 5998 cents returned 2999 cents.

**What this does not show:** one planted bug can't tell you how good the test
suite is in general. That's why the next step is a mutation suite of 10–15
different planted bugs, measured as "caught X of Y."

Reproduce it with `python scripts/regression_demo.py`.

### 5. Synthetic shop dataset

Cartiva has no real customers, so its shop activity is generated by
[`analytics/generate_data.py`](analytics/generate_data.py) with a fixed random
seed: the same seed always produces exactly the same data.

| Table | Rows | One row per… |
|---|---:|---|
| customers | 8,000 | customer, with signup date, state, channel and A/B group |
| sessions | ~22,000 | visit, with device and traffic channel |
| events | ~80,000 | product view, add to cart, checkout start or purchase |
| orders | ~2,400 | order, with subtotal, discount, shipping and total |
| order_items | ~2,800 | product line in an order |
| products / variants / promotions | 36 / 87 / 5 | catalog item / size-color option / discount |

What's in it: two years (2024–2025) of a store that launches in January 2024,
seasonality with a December peak, Summer and Black Friday sales, a WELCOME10
A/B experiment, repeat customers, and device differences. Every order is
priced with the same tested rules as the requirements.

- **Every assumption is written down** in
  [`docs/data-assumptions.md`](docs/data-assumptions.md), including the effects
  deliberately built in, so findings can be checked against them.
- **Table and column definitions:** [`docs/data-dictionary.md`](docs/data-dictionary.md)
- **Loaded into PostgreSQL** in its own `analytics` schema, with primary keys,
  foreign keys and checks such as `total = subtotal − discount + shipping`.
  The CSV files in [`analytics/data/`](analytics/data/) are ready for Tableau.

### 6. Storefront

A minimal store page at `/shop` that browses, filters and searches the 36
products and adds items to a bag through the real cart API. Prices always come
from the server. Checkout is intentionally not part of this demo.

### 7. Analysis (in progress)

The analysis workflow is set up and running end to end:

```mermaid
flowchart LR
    PG[("PostgreSQL<br/>analytics schema")] --> Q["SQL queries<br/>analytics/queries/"]
    Q --> X["CSV exports<br/>analytics/exports/"]
    X --> T["Tableau Public"]
```

- **SQL:** queries are saved as numbered files in
  [`analytics/queries/`](analytics/queries/) and run against PostgreSQL.
- **Exports:** query results are saved to
  [`analytics/exports/`](analytics/exports/) for Tableau.
- **First chart:** [Top 10 products by units sold](https://public.tableau.com/app/profile/rucha.panhale/viz/CartivaTopProducts/Top10ProductsbyUnitsSold)
  on Tableau Public.

**Now working on:** KPI, conversion funnel, cart abandonment, average order
value by category, WELCOME10 group comparison and sale-period queries, which
feed a one-page Tableau dashboard and a written findings memo.

---

## AI evaluation design (planned)

```mermaid
flowchart LR
    REQ["Requirement<br/>e.g. CART-004"] --> LLM["LLM proposes<br/>test cases (JSON)"]
    LLM --> VAL{"Schema<br/>valid?"}
    VAL -- no --> REJ["Rejected<br/>(counted)"]
    VAL -- yes --> HUMAN["Human review<br/>rubric scoring"]
    HUMAN -- approved --> RUNNER["Trusted runner<br/>executes the test"]
    HUMAN -- rejected --> REJ
    RUNNER --> MET["Metrics: validity %,<br/>approval %, κ,<br/>bugs caught"]
```

**Hard rule:** the LLM never writes code that gets executed. It only produces
structured, schema-validated proposals (endpoint, input, expected result).
A human approves each one, and a hand-written runner executes approved
proposals. Pass or fail comes from real test results, never from the AI's opinion.

Planned measurements:
- **Rubric:** schema-valid, linked to the right requirement, correct expected
  result, in scope, not a duplicate, would catch a defect
- **Inter-rater agreement** (Cohen's kappa) between two human raters
- **LLM-as-judge vs human labels**
- **Prompt or model comparison**
- **Defect catch rate:** AI-proposed tests vs hand-written tests, against the mutation suite

---

## Tech stack

| Purpose | Tools |
|---|---|
| Data & storage | PostgreSQL 18 (Docker), SQLModel, Alembic migrations |
| Backend | Python 3.11, FastAPI, Pydantic |
| Testing & CI | pytest, GitHub Actions, JUnit XML |
| Data generation | Python (standard library only), seeded and tested |
| Analysis | PostgreSQL SQL (written in DBeaver), Tableau Public |
| Storefront | HTML, CSS, JavaScript (no framework), served by FastAPI |

---

## Quick start

```bash
# 1. Start PostgreSQL (Docker Desktop must be running)
cp .env.example .env          # then set your own local passwords
docker compose up -d postgres

# 2. Set up Python
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r cartiva/backend/requirements.txt

# 3. Run the tests (no database needed: tests use isolated in-memory databases)
python -m pytest cartiva/backend/tests analytics/tests -q

# 4. Load the shop dataset into PostgreSQL (schema "analytics")
bash analytics/load_data.sh

# 5. Open the store (after migrations and seeding: see docs/setup.md)
python -m uvicorn cartiva.backend.main:app --reload
#    then visit http://127.0.0.1:8000/shop/
```

Full setup (database roles, migrations, permissions, seed data):
[`docs/setup.md`](docs/setup.md).
Endpoint behavior and status codes: [`docs/api.md`](docs/api.md).

---

## How this was built

I wrote Cartiva's business requirements and policies, made the design and
data decisions, and reviewed and tested every change. I used **Claude Code**
as an AI coding assistant to write most of the application, backend, data
generator and storefront code. The SQL analysis, Tableau dashboard and
findings are my own work.

## Quality principles

- Run tests against real application logic or APIs.
- Review AI-generated test suggestions before execution.
- Never execute arbitrary AI-generated code.
- Base dashboards on stored execution results.
- Keep requirements, tests, runs, and defects isolated by application.
- Distinguish application failures from execution infrastructure errors.

## Known limitations

- **Tests run on SQLite, not PostgreSQL.** PostgreSQL-specific behavior
  (row locking under concurrency, permissions) was checked manually, not in
  automated tests.
- **Concurrency was smoke-tested once by hand:** two simultaneous requests for
  5 units each against stock of 8. One succeeded, one was rejected, and the
  stored quantity stayed 5.
- **Not built:** checkout, inventory deduction, guest-session cookies, and
  duplicate-checkout protection (CART-008, CART-009, CART-011). These are
  outside the current scope.
- **Tests are not yet tagged with requirement IDs**, so requirement-level
  coverage can't be reported automatically yet.
- **The shop data is synthetic.** Findings from it demonstrate metric design
  and analysis method, not real customer behavior. The built-in effects are
  disclosed in [`docs/data-assumptions.md`](docs/data-assumptions.md).
- **The storefront has no checkout**, and orders in the dataset are generated,
  not placed through the store.

## Roadmap

1. SQL analysis: KPIs, conversion funnel, cart abandonment, average order
   value by category, WELCOME10 groups, sale periods vs normal weeks
2. Tableau Public dashboard + findings memo
3. WELCOME10 A/B significance test; cohort and repeat-customer analysis
4. Policy changes over time (new promotions with effective dates) and
   before/after analysis
5. Later phase: mutation suite and LLM test-proposal evaluation
