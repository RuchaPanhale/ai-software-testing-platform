#!/usr/bin/env bash
# Load the synthetic shop dataset into the local Cartiva PostgreSQL database.
#
# Run from the repository root, with Docker Desktop running and the
# postgres service started (docker compose up -d postgres):
#     bash analytics/load_data.sh
#
# Recreates the "analytics" schema (app tables in "public" are untouched),
# loads every CSV in analytics/data/, and grants read-only access to the
# application role. Uses the administrator credentials from .env.

set -euo pipefail

if [[ ! -f .env ]]; then
    echo "Run this from the repository root (no .env found here)." >&2
    exit 1
fi

set -a
source .env
set +a

psql_admin() {
    docker compose exec -T postgres psql \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q "$@"
}

echo "Creating analytics schema..."
psql_admin < analytics/schema.sql

# Parents before children, so foreign keys are satisfied.
TABLES=(products product_variants promotions customers sessions
        orders order_items events)

for table in "${TABLES[@]}"; do
    psql_admin -c "\copy analytics.${table} FROM pstdin WITH (FORMAT csv, HEADER true)" \
        < "analytics/data/${table}.csv"
    echo "  loaded ${table}"
done

echo "Granting read-only access to ${CARTIVA_DB_USER}..."
psql_admin <<SQL
GRANT USAGE ON SCHEMA analytics TO ${CARTIVA_DB_USER};
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO ${CARTIVA_DB_USER};
ANALYZE;
SQL

echo "Row counts:"
psql_admin -c "
SELECT 'customers' AS table_name, count(*) AS row_count FROM analytics.customers
UNION ALL SELECT 'sessions', count(*) FROM analytics.sessions
UNION ALL SELECT 'events', count(*) FROM analytics.events
UNION ALL SELECT 'orders', count(*) FROM analytics.orders
UNION ALL SELECT 'order_items', count(*) FROM analytics.order_items;"

echo "Done."
