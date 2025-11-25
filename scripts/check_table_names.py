#!/usr/bin/env python
"""
Check actual table names in both databases to verify mapping.
"""
import psycopg2

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

print("=== V2 Tables (xero related) ===")
with v2_conn.cursor() as cur:
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%xero%'
        ORDER BY table_name;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}")

print("\n=== V3 Tables (xero related) ===")
with v3_conn.cursor() as cur:
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%xero%'
        ORDER BY table_name;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}")

v2_conn.close()
v3_conn.close()

