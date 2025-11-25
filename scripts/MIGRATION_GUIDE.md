# Data Migration Guide: v2 to v3

This guide explains how to export data from v2 database and import it into v3 database.

## Prerequisites

1. Both databases must exist:
   - v2: `klikk_bi`
   - v3: `klikk_bi_v3`

2. Django environment set up in v3 with all dependencies installed

3. Migrations run in v3 to create the schema

## Step-by-Step Migration

### Step 1: Create v3 Database

```bash
psql -U mc -h 127.0.0.1 -d postgres -c "CREATE DATABASE klikk_bi_v3;"
```

### Step 2: Run Migrations in v3

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Export Data from v2

**Option A: Using Django dumpdata (Recommended)**

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence
python manage.py dumpdata apps.xero --natural-foreign --natural-primary --indent 2 > /tmp/v2_xero_data.json
```

Then adjust app labels:
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python scripts/adjust_app_labels.py /tmp/v2_xero_data.json /tmp/v3_xero_data.json
```

Then import:
```bash
python manage.py loaddata /tmp/v3_xero_data.json
```

**Option B: Using pg_dump (Direct SQL)**

```bash
# Export data
pg_dump -U mc -h 127.0.0.1 -d klikk_bi --data-only --column-inserts > /tmp/v2_data.sql

# Import using the Python script (handles table name mapping)
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python scripts/import_data.py
```

### Step 4: Verify Data

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python manage.py shell
```

```python
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_metadata.models import XeroAccount

# Check counts
print(f"Tenants: {XeroTenant.objects.count()}")
print(f"Accounts: {XeroAccount.objects.count()}")
```

## Table Name Mapping

The script automatically maps v2 table names to v3 table names:

| v2 Table | v3 Table |
|----------|----------|
| apps_xero_xerotenant | apps_xero_xero_core_xerotenant |
| apps_xero_xeroclientcredentials | apps_xero_xero_auth_xeroclientcredentials |
| apps_xero_xerotenanttoken | apps_xero_xero_auth_xerotenanttoken |
| apps_xero_xeroauthsettings | apps_xero_xero_auth_xeroauthsettings |
| apps_xero_xerolastupdate | apps_xero_xero_sync_xerolastupdate |
| apps_xero_xerotenantschedule | apps_xero_xero_sync_xerotenantschedule |
| apps_xero_xerotaskexecutionlog | apps_xero_xero_sync_xerotaskexecutionlog |
| apps_xero_xerobusinessunits | apps_xero_xero_metadata_xerobusinessunits |
| apps_xero_xeroaccount | apps_xero_xero_metadata_xeroaccount |
| apps_xero_xerotracking | apps_xero_xero_metadata_xerotracking |
| apps_xero_xerocontacts | apps_xero_xero_metadata_xerocontacts |
| apps_xero_xerotransactionsource | apps_xero_xero_data_xerotransactionsource |
| apps_xero_xerojournalssource | apps_xero_xero_data_xerojournalssource |
| apps_xero_xerojournals | apps_xero_xero_data_xerojournals |
| apps_xero_xerotrailbalance | apps_xero_xero_cube_xerotrailbalance |
| apps_xero_xerobalancesheet | apps_xero_xero_cube_xerobalancesheet |

## Troubleshooting

1. **Foreign key errors**: Make sure to migrate in dependency order (tenants first, then dependent tables)

2. **Table not found**: Check that migrations have been run in v3

3. **Column mismatches**: The import script only copies common columns between v2 and v3 tables

4. **User model conflicts**: If you have user data in v2, you may need to migrate that separately

## Quick Migration Script

Run the complete migration:

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
bash scripts/migrate_database.sh
python scripts/import_data.py
```

