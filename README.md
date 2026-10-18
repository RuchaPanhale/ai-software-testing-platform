# AI Software Testing & Regression Platform

An AI-assisted, multi-application software quality platform.

MS Computer Science termination project at Binghamton University.
Author: Rucha Panhale
Faculty supervisor: Professor Shiqi Zhang

## Project status

In development. Cartiva's FastAPI health endpoint is implemented
and manually verified. Local PostgreSQL setup is operational.
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