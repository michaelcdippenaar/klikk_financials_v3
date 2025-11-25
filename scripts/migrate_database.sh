#!/bin/bash
# Complete database migration script from v2 to v3

set -e

V2_DB="klikk_bi"
V3_DB="klikk_bi_v3"
DB_USER="mc"
DB_HOST="127.0.0.1"
DB_PASSWORD="Number55dip"

echo "=== Step 1: Creating v3 database ==="
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -d postgres -c "DROP DATABASE IF EXISTS $V3_DB;" 2>&1 || true
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -d postgres -c "CREATE DATABASE $V3_DB;" 2>&1

echo "=== Step 2: Exporting schema and data from v2 ==="
PGPASSWORD=$DB_PASSWORD pg_dump -U $DB_USER -h $DB_HOST -d $V2_DB --schema-only > /tmp/v2_schema.sql 2>&1
PGPASSWORD=$DB_PASSWORD pg_dump -U $DB_USER -h $DB_HOST -d $V2_DB --data-only --column-inserts > /tmp/v2_data.sql 2>&1

echo "=== Step 3: Running migrations in v3 ==="
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python3 manage.py migrate --run-syncdb 2>&1 | tail -20

echo "=== Step 4: Importing data (this will require table name mapping) ==="
echo "Data files created:"
echo "  Schema: /tmp/v2_schema.sql"
echo "  Data: /tmp/v2_data.sql"
echo ""
echo "Next: Run python3 scripts/import_data.py to import with table mapping"

