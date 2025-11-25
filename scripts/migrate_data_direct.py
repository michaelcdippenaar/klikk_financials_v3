#!/usr/bin/env python
"""
Direct data migration script from v2 to v3.
Uses Django ORM to copy data, handling app label changes automatically.
"""
import os
import sys
import django

# Setup v3 Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'klikk_business_intelligence.settings')
django.setup()

# Now import v2 models using direct database connection
from django.db import connections
import psycopg2

# Database connections
v2_db_config = {
    'dbname': 'klikk_bi',
    'user': 'mc',
    'password': 'Number55dip',
    'host': '127.0.0.1',
    'port': '5432'
}

v3_db_config = {
    'dbname': 'klikk_bi_v3',
    'user': 'mc',
    'password': 'Number55dip',
    'host': '127.0.0.1',
    'port': '5432'
}

# Import v3 models
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken, XeroAuthSettings
from apps.xero.xero_sync.models import XeroLastUpdate, XeroTenantSchedule, XeroTaskExecutionLog
from apps.xero.xero_metadata.models import XeroBusinessUnits, XeroAccount, XeroTracking, XeroContacts
from apps.xero.xero_data.models import XeroTransactionSource, XeroJournalsSource, XeroJournals
from apps.xero.xero_cube.models import XeroTrailBalance, XeroBalanceSheet
from apps.user.models import User

def migrate_table(v2_conn, v3_model, table_mapping=None):
    """Migrate a single table's data."""
    model_name = v3_model.__name__
    print(f"\nMigrating {model_name}...")
    
    # Get table name from model
    table_name = v3_model._meta.db_table
    
    # Determine v2 table name
    # v2 uses apps_xero_modelname, v3 uses apps_xero_appname_modelname
    v2_table_name = None
    if 'xero_core' in str(v3_model._meta):
        v2_table_name = f"apps_xero_{model_name.lower()}"
    elif 'xero_auth' in str(v3_model._meta):
        if model_name == 'XeroClientCredentials':
            v2_table_name = "apps_xero_xeroclientcredentials"
        elif model_name == 'XeroTenantToken':
            v2_table_name = "apps_xero_xerotenanttoken"
        elif model_name == 'XeroAuthSettings':
            v2_table_name = "apps_xero_xeroauthsettings"
    elif 'xero_sync' in str(v3_model._meta):
        if model_name == 'XeroLastUpdate':
            v2_table_name = "apps_xero_xerolastupdate"
        elif model_name == 'XeroTenantSchedule':
            v2_table_name = "apps_xero_xerotenantschedule"
        elif model_name == 'XeroTaskExecutionLog':
            v2_table_name = "apps_xero_xerotaskexecutionlog"
    elif 'xero_metadata' in str(v3_model._meta):
        v2_table_name = f"apps_xero_{model_name.lower()}"
    elif 'xero_data' in str(v3_model._meta):
        v2_table_name = f"apps_xero_{model_name.lower()}"
    elif 'xero_cube' in str(v3_model._meta):
        v2_table_name = f"apps_xero_{model_name.lower()}"
    
    if table_mapping:
        v2_table_name = table_mapping.get(model_name, v2_table_name)
    
    if not v2_table_name:
        print(f"  Could not determine v2 table name for {model_name}, skipping...")
        return 0
    
    try:
        # Check if v2 table exists
        with v2_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (v2_table_name,))
            exists = cur.fetchone()[0]
            
            if not exists:
                print(f"  Table {v2_table_name} does not exist in v2, skipping...")
                return 0
            
            # Get all data from v2
            cur.execute(f"SELECT * FROM {v2_table_name}")
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            if not rows:
                print(f"  No data in {v2_table_name}, skipping...")
                return 0
            
            print(f"  Found {len(rows)} rows in {v2_table_name}")
            
            # Clear v3 table first
            v3_model.objects.all().delete()
            print(f"  Cleared {table_name}")
            
            # Insert data into v3
            count = 0
            for row in rows:
                row_dict = dict(zip(columns, row))
                try:
                    # Handle foreign keys - need to map old IDs to new IDs
                    # For now, create objects directly
                    v3_model.objects.create(**row_dict)
                    count += 1
                except Exception as e:
                    print(f"  Error inserting row: {e}")
                    continue
            
            print(f"  Migrated {count} rows to {table_name}")
            return count
            
    except Exception as e:
        print(f"  Error migrating {model_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    print("Starting data migration from v2 to v3...")
    
    # Connect to databases
    try:
        v2_conn = psycopg2.connect(**v2_db_config)
        print("Connected to v2 database (klikk_bi)")
    except Exception as e:
        print(f"Failed to connect to v2 database: {e}")
        return
    
    # Migration order matters due to foreign keys
    # 1. Core tenant (no dependencies)
    migrate_table(v2_conn, XeroTenant, {'XeroTenant': 'apps_xero_xerotenant'})
    
    # 2. Auth (depends on User and XeroTenant)
    # Note: User model might need special handling
    migrate_table(v2_conn, XeroClientCredentials, {'XeroClientCredentials': 'apps_xero_xeroclientcredentials'})
    migrate_table(v2_conn, XeroTenantToken, {'XeroTenantToken': 'apps_xero_xerotenanttoken'})
    migrate_table(v2_conn, XeroAuthSettings, {'XeroAuthSettings': 'apps_xero_xeroauthsettings'})
    
    # 3. Sync (depends on XeroTenant)
    migrate_table(v2_conn, XeroLastUpdate, {'XeroLastUpdate': 'apps_xero_xerolastupdate'})
    migrate_table(v2_conn, XeroTenantSchedule, {'XeroTenantSchedule': 'apps_xero_xerotenantschedule'})
    migrate_table(v2_conn, XeroTaskExecutionLog, {'XeroTaskExecutionLog': 'apps_xero_xerotaskexecutionlog'})
    
    # 4. Metadata (depends on XeroTenant)
    migrate_table(v2_conn, XeroBusinessUnits, {'XeroBusinessUnits': 'apps_xero_xerobusinessunits'})
    migrate_table(v2_conn, XeroAccount, {'XeroAccount': 'apps_xero_xeroaccount'})
    migrate_table(v2_conn, XeroTracking, {'XeroTracking': 'apps_xero_xerotracking'})
    migrate_table(v2_conn, XeroContacts, {'XeroContacts': 'apps_xero_xerocontacts'})
    
    # 5. Data (depends on XeroTenant, XeroContacts, XeroAccount, XeroTracking)
    migrate_table(v2_conn, XeroTransactionSource, {'XeroTransactionSource': 'apps_xero_xerotransactionsource'})
    migrate_table(v2_conn, XeroJournalsSource, {'XeroJournalsSource': 'apps_xero_xerojournalssource'})
    migrate_table(v2_conn, XeroJournals, {'XeroJournals': 'apps_xero_xerojournals'})
    
    # 6. Cube (depends on XeroTenant, XeroAccount, XeroContacts, XeroTracking)
    migrate_table(v2_conn, XeroTrailBalance, {'XeroTrailBalance': 'apps_xero_xerotrailbalance'})
    migrate_table(v2_conn, XeroBalanceSheet, {'XeroBalanceSheet': 'apps_xero_xerobalancesheet'})
    
    v2_conn.close()
    print("\nData migration completed!")


if __name__ == '__main__':
    main()

