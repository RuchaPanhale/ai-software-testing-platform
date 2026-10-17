# AI Software Testing & Regression Platform

An AI-assisted, multi-application software quality platform.

MS Computer Science termination project at Binghamton University.
Author: Rucha Panhale
Faculty supervisor: Professor Shiqi Zhang

## Project status

In development. Local environment and Git repository initialized.
Application features are not implemented yet.

## Planned systems

### Cartiva
A full-stack fashion e-commerce application with a React and
TypeScript frontend, FastAPI backend, and SQLite database.

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