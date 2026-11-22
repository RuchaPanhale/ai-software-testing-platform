#!/usr/bin/env bash
# Run every analysis query in analytics/queries/ and save each result as a
# CSV in analytics/exports/ (for Tableau). Re-run any time the data changes.
#
# Run from the repository root, with the postgres service running:
#     bash analytics/export_results.sh
#
# Each .sql file must contain exactly one SELECT statement ending in ";".
# Output name: 03_monthly_trend.sql -> analytics/exports/monthly_trend.csv

set -euo pipefail

if [[ ! -f .env ]]; then
    echo "Run this from the repository root (no .env found here)." >&2
    exit 1
fi

set -a
source .env
set +a

mkdir -p analytics/exports

for file in analytics/queries/*.sql; do
    name=$(basename "$file" .sql)
    name=${name#[0-9][0-9]_}          # drop the "03_" number prefix
    [[ "$name" == "row_counts" ]] && continue   # data check, not for Tableau

    query=$(cat "$file")
    query=${query%;*}                 # remove the final semicolon

    docker compose exec -T postgres psql \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q \
        -c "COPY (${query}) TO STDOUT WITH (FORMAT csv, HEADER true)" \
        > "analytics/exports/${name}.csv"

    rows=$(( $(wc -l < "analytics/exports/${name}.csv") - 1 ))
    echo "  ${name}.csv  (${rows} rows)"
done

echo "Done. Files are in analytics/exports/"
