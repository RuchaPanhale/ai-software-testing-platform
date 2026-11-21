# Local Setup

Full local setup for Cartiva on macOS. For a quick overview, see the main
[README](../README.md).

## 1. Python environment

Python 3.11 is required. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r cartiva/backend/requirements.txt
```

## 2. PostgreSQL (Docker)

Docker Desktop must be running.

For first-time setup, copy the configuration template:

```bash
cp .env.example .env
```

Replace the password placeholders in `.env` with unique local-development
passwords. Do not overwrite an existing configured `.env` or commit its contents.

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Check database health:

```bash
docker compose ps
```

Verify connectivity:

```bash
docker compose exec postgres psql -U cartiva_admin -d cartiva -c "SELECT current_database(), current_user;"
```

Connection details for applications running on the Mac:
- Host: 127.0.0.1
- Port: 5433
- Database: cartiva

Stop PostgreSQL when finished:

```bash
docker compose stop postgres
```

Database data persists in the named Docker volume.
`docker compose down -v` deletes that volume and its database data.

Initialization credentials apply when the database volume is first
created. Editing `.env` later does not automatically change an
existing database user's password.

## 3. Database roles

Cartiva uses two roles:
- `cartiva_admin` (owner): creates and migrates tables. Used only for setup.
- `cartiva_app` (restricted): used by the API, with only the permissions it needs.

Create the application role once per fresh database volume. Open PostgreSQL
as the administrator:

```bash
docker compose exec postgres psql -U cartiva_admin -d cartiva
```

At the PostgreSQL prompt, run:

```sql
CREATE ROLE cartiva_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
```

Set its password interactively:

```text
\password cartiva_app
```

Grant connection and schema access:

```sql
GRANT CONNECT ON DATABASE cartiva TO cartiva_app;
GRANT USAGE ON SCHEMA public TO cartiva_app;
```

Exit:

```text
\q
```

Set `CARTIVA_DB_PASSWORD` in your local `.env` to the password you chose.
Keep `.env.example` as a template without real passwords.

The application role must never be used to create or migrate tables.

## 4. Verify the Python-to-PostgreSQL connection

The backend reads `CARTIVA_DB_*` settings from the root `.env` file.
Python running on the host connects to 127.0.0.1:5433.

From the project root:

```bash
python - <<'PY'
from sqlalchemy import text
from cartiva.backend.database import get_engine

with get_engine().connect() as connection:
    row = connection.execute(
        text("SELECT current_database(), current_user")
    ).one()
    print(f"Database: {row[0]}")
    print(f"User: {row[1]}")
    print("Python-to-PostgreSQL connection successful.")
PY
```

Expected database: `cartiva`. Expected user: `cartiva_app`.

## 5. Apply migrations

Migrations run as the owner role:

```bash
python -m alembic -c cartiva/backend/alembic.ini upgrade head
```

## 6. Table permissions for the application role

After applying migrations, grant the application role access to the cart
and order tables. Run from the repository root:

```bash
docker compose exec postgres psql \
  -U cartiva_admin \
  -d cartiva \
  -v ON_ERROR_STOP=1 \
  -c "
BEGIN;
GRANT SELECT, INSERT ON TABLE public.carts TO cartiva_app;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE public.cart_items TO cartiva_app;
GRANT USAGE ON SEQUENCE public.cart_items_id_seq TO cartiva_app;
GRANT UPDATE (id) ON TABLE public.carts TO cartiva_app;
GRANT SELECT, INSERT
    ON TABLE public.orders, public.order_items TO cartiva_app;
GRANT USAGE
    ON SEQUENCE public.order_items_id_seq TO cartiva_app;
COMMIT;
"
```

`UPDATE (id)` on `carts` is needed because adding items locks the parent
cart row, and PostgreSQL requires an UPDATE privilege for that row lock.
New tables need their own grants.

## 7. Seed the product catalog

```bash
python -m cartiva.backend.seed
```

On an empty catalog, this creates the 36 products and 87 variants defined in
`cartiva/catalog_data.py` (the same catalog the synthetic dataset uses),
including sold-out variants for inventory testing.

To replace an older catalog, empty the app's tables first. This deletes all
local products, carts and orders in the `public` schema (not the analytics
data), and restarts the IDs at 1:

```bash
docker compose exec postgres psql -U cartiva_admin -d cartiva -c \
  "TRUNCATE order_items, orders, cart_items, carts, product_variants, products RESTART IDENTITY;"
python -m cartiva.backend.seed
```

The script uses administrator credentials from `.env` for this setup
operation; the API continues using its restricted role. All inserts run in
one transaction. If either catalog table already contains data, the script
skips initialization without changing existing records. It does not reset
inventory or synchronize catalog updates. Run it once at a time.

## 8. Run the API and the store

```bash
python -m uvicorn cartiva.backend.main:app --reload
```

- Storefront: http://127.0.0.1:8000/shop/ (http://127.0.0.1:8000/ redirects there)
- Catalog JSON: http://127.0.0.1:8000/products
- Interactive API documentation: http://127.0.0.1:8000/docs

Product photos go in `cartiva/storefront/images/`; see the README there for
file names and an image prompt template.

## 8b. Load the synthetic shop dataset

```bash
python -m analytics.generate_data   # only needed after changing assumptions
bash analytics/load_data.sh
```

This recreates the `analytics` schema, loads the CSVs from `analytics/data/`
and grants read-only access to `cartiva_app`. For SQL practice, connect a SQL
client (e.g. DBeaver) to 127.0.0.1:5433, database `cartiva`, user `cartiva_app`.

## 9. Run the tests

```bash
python -m pytest cartiva/backend/tests analytics/tests -q
```

Tests use a shared fixture in `tests/conftest.py` that gives each test a
fresh in-memory SQLite database through a FastAPI dependency override.
Tests do not modify the local PostgreSQL database and do not need Uvicorn or
Docker running.

These tests cover API behavior. PostgreSQL-specific migrations,
permissions, and concurrency are checked separately (migrations in CI;
permissions and concurrency manually).

## 10. Run the regression experiment

```bash
python scripts/regression_demo.py
```

The script copies the committed code to a temporary folder and runs the same
tests against the unchanged baseline and against a copy with one planted
defect (the cart subtotal sums unit prices instead of quantity-adjusted line
totals). Your working copy and development database are not modified.
Logs, JUnit XML reports, and a JSON summary are saved under
`reports/regression-demo/` (not committed).
