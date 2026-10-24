# AI Software Testing & Regression Platform

An AI-assisted, multi-application software quality platform.

MS Computer Science termination project at Binghamton University.
Author: Rucha Panhale
Faculty supervisor: Professor Shiqi Zhang

## Project status

In development. Cartiva's FastAPI health endpoint is implemented
and manually verified. Local PostgreSQL is operational, and Python
database connectivity is verified using a restricted application account.
Catalog, cart, checkout, and the testing platform are not implemented yet.

## Planned systems

### Cartiva
A full-stack fashion e-commerce application with a React and
TypeScript frontend, FastAPI backend, and PostgreSQL database.

Cartiva will be the first application under test.

### Quality Platform
A reusable testing platform for registering applications, managing
requirements, reviewing AI-generated test suggestions, executing
approved tests, comparing application versions, and reporting defects.

Application-specific adapters will connect each application to
the shared testing engine.

## Development order

1. Define requirements, business rules, and architecture.
2. Build and test Cartiva.
3. Build the reusable testing and regression platform.
4. Add structured AI test suggestions and human review.
5. Add quality dashboards and defect prioritization.
6. Complete engineering checks, documentation, and demo preparation.
7. Add a second beauty application if time permits.

## Quality principles

- Run tests against real application logic or APIs.
- Review AI-generated test suggestions before execution.
- Never execute arbitrary AI-generated code.
- Base dashboards on stored execution results.
- Keep requirements, tests, runs, and defects isolated by application.
- Distinguish application failures from execution infrastructure errors.

## Local setup completed

- Python 3.11.5 virtual environment: .venv
- Node.js v24.22.0
- npm 11.19.1
- Git repository with main branch

Activate the Python environment from the project folder:

```bash
source .venv/bin/activate

## Local PostgreSQL Setup

Docker Desktop must be running.

For first-time setup, copy the configuration template:

```bash
cp .env.example .env
```

Replace the password placeholder in `.env` with a unique
local-development password. Do not overwrite an existing configured
`.env` or commit its contents.

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

The initialization account is for local database administration.
A restricted application account will be configured separately.

Stop PostgreSQL when finished:

```bash
docker compose stop postgres
```

Database data persists in the named Docker volume.
`docker compose down -v` deletes that volume and its database data.

Initialization credentials apply when the database volume is first
created. Editing `.env` later does not automatically change an
existing database user's password.

## Cartiva Application Database Account

After initializing PostgreSQL, create a restricted application account.
Perform this setup once per fresh database volume.

Open PostgreSQL as the local administrator:

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

Set CARTIVA_DB_PASSWORD in your local .env to the password you chose.
Keep .env.example as a template without actual passwords.

This account currently has connection and schema-usage permissions.
Table permissions will be added alongside database migrations.
The application account must not be used to create or migrate tables.

## Python Database Connection

Activate the project environment and install dependencies:

```bash
source .venv/bin/activate
python -m pip install -r cartiva/backend/requirements.txt
```

The backend reads CARTIVA_DB_ settings from the root .env file.
Python running on the host connects to 127.0.0.1:5433.

Verify connectivity from the project root:

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

Expected database: cartiva.
Expected user: cartiva_app.


### Seed the local product catalog

After configuring `.env`, starting PostgreSQL, and applying migrations,
run this command from the repository root with the Python virtual
environment activated:

```bash
python -m cartiva.backend.seed
```

On an empty catalog, this creates three sample products and eight variants,
including a sold-out variant for inventory testing.

The script uses administrator credentials from `.env` for this setup
operation. The API continues using its restricted application account.

All inserts run in one transaction. If either catalog table already
contains data, the script skips initialization without changing existing
records. It does not reset inventory or synchronize catalog updates.

Run this script once at a time for local development.


### Catalog API

With PostgreSQL running and the sample catalog seeded, start the API:

```bash
python -m uvicorn cartiva.backend.main:app --reload
```

- Catalog: http://127.0.0.1:8000/products
- Interactive API documentation: http://127.0.0.1:8000/docs

`GET /products` returns products ordered by name and ID, with their
variants ordered by ID. Each variant includes size, color, price in
integer cents, stock quantity, and an optional image URL.

Sold-out variants remain visible with a stock quantity of zero.
An empty catalog returns an empty list.

Search, filtering, and pagination are not implemented yet.