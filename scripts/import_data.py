#!/usr/bin/env python
"""
Import data from v2 to v3 with table name mapping.
"""
import os
import sys
import django
import psycopg2
from psycopg2.extras import execute_values

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'klikk_business_intelligence.settings')
django.setup()

# Table name mapping: v2_table_name -> v3_table_name
# Django uses <app_label>_<model_name_lowercase> format
# v2: apps.xero -> app_label 'xero', so tables are 'xero_xerotenant'
# v3: apps.xero.xero_core -> app_label 'xero_core', so tables are 'xero_core_xerotenant'
TABLE_MAPPING = {
    'xero_xerotenant': 'xero_core_xerotenant',
    'xero_xeroclientcredentials': 'xero_auth_xeroclientcredentials',
    'xero_xerotenanttoken': 'xero_auth_xerotenanttoken',
    'xero_xeroauthsettings': 'xero_auth_xeroauthsettings',
    'xero_xerolastupdate': 'xero_sync_xerolastupdate',
    'xero_xerotenantschedule': 'xero_sync_xerotenantschedule',
    'xero_xerotaskexecutionlog': 'xero_sync_xerotaskexecutionlog',
    'xero_xerobusinessunits': 'xero_metadata_xerobusinessunits',
    'xero_xeroaccount': 'xero_metadata_xeroaccount',
    'xero_xerotracking': 'xero_metadata_xerotracking',
    'xero_xerocontacts': 'xero_metadata_xerocontacts',
    'xero_xerotransactionsource': 'xero_data_xerotransactionsource',
    'xero_xerojournalssource': 'xero_data_xerojournalssource',
    'xero_xerojournals': 'xero_data_xerojournals',
    'xero_xerotrailbalance': 'xero_cube_xerotrailbalance',
    'xero_xerobalancesheet': 'xero_cube_xerobalancesheet',
}

def get_table_columns(conn, table_name):
    """Get column names for a table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        return [row[0] for row in cur.fetchall()]

def migrate_table(v2_conn, v3_conn, v2_table, v3_table):
    """Migrate data from one table to another."""
    print(f"\nMigrating {v2_table} -> {v3_table}...")
    
    try:
        # Check if tables exist
        with v2_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                );
            """, (v2_table,))
            if not cur.fetchone()[0]:
                print(f"  {v2_table} does not exist, skipping...")
                return 0
        
        with v3_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                );
            """, (v3_table,))
            if not cur.fetchone()[0]:
                print(f"  {v3_table} does not exist, skipping...")
                return 0
        
        # Get columns
        v2_columns = get_table_columns(v2_conn, v2_table)
        v3_columns = get_table_columns(v3_conn, v3_table)
        
        # Find common columns
        common_columns = [col for col in v2_columns if col in v3_columns]
        
        if not common_columns:
            print(f"  No common columns found, skipping...")
            return 0
        
        # Clear v3 table
        with v3_conn.cursor() as cur:
            cur.execute(f'TRUNCATE TABLE "{v3_table}" CASCADE;')
            v3_conn.commit()
            print(f"  Cleared {v3_table}")
        
        # Copy data
        with v2_conn.cursor() as cur:
            columns_str = ', '.join(f'"{col}"' for col in common_columns)
            cur.execute(f'SELECT {columns_str} FROM "{v2_table}";')
            rows = cur.fetchall()
            
            if not rows:
                print(f"  No data to migrate")
                return 0
            
            print(f"  Found {len(rows)} rows")
            
            # Insert into v3
            with v3_conn.cursor() as v3_cur:
                placeholders = ', '.join(['%s'] * len(common_columns))
                insert_sql = f'INSERT INTO "{v3_table}" ({columns_str}) VALUES ({placeholders});'
                
                v3_cur.executemany(insert_sql, rows)
                v3_conn.commit()
                
                print(f"  Migrated {len(rows)} rows")
                return len(rows)
                
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        v3_conn.rollback()
        return 0

def main():
    print("Starting database migration...")
    
    v2_conn = psycopg2.connect(
        dbname='klikk_bi',
        user='mc',
        password='Number55dip',
        host='127.0.0.1',
        port='5432'
    )
    
    v3_conn = psycopg2.connect(
        dbname='klikk_bi_v3',
        user='mc',
        password='Number55dip',
        host='127.0.0.1',
        port='5432'
    )
    
    total_migrated = 0
    
    # Migrate in dependency order (using v2 table names)
    migration_order = [
        'xero_xerotenant',
        'xero_xeroclientcredentials',
        'xero_xerotenanttoken',
        'xero_xeroauthsettings',
        'xero_xerolastupdate',
        'xero_xerotenantschedule',
        'xero_xerotaskexecutionlog',
        'xero_xerobusinessunits',
        'xero_xeroaccount',
        'xero_xerotracking',
        'xero_xerocontacts',
        'xero_xerotransactionsource',
        'xero_xerojournalssource',
        'xero_xerojournals',
        'xero_xerotrailbalance',
        'xero_xerobalancesheet',
    ]
    
    for v2_table in migration_order:
        v3_table = TABLE_MAPPING.get(v2_table)
        if v3_table:
            count = migrate_table(v2_conn, v3_conn, v2_table, v3_table)
            total_migrated += count
    
    v2_conn.close()
    v3_conn.close()
    
    print(f"\n=== Migration Complete ===")
    print(f"Total rows migrated: {total_migrated}")

if __name__ == '__main__':
    main()

