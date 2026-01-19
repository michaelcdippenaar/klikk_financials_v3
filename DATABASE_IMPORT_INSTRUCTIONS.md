# Database Import Instructions

This document explains how to import the database dump on a fresh server.

## Prerequisites

1. PostgreSQL installed on the server
2. Database user created with appropriate permissions
3. `database_dump.sql` file available on the server

## Steps to Import

### 1. Create the Database

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# Create the database
CREATE DATABASE klikk_bi_v3;

# Create the user (if not exists)
CREATE USER mc WITH PASSWORD 'Number55dip';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE klikk_bi_v3 TO mc;

# Exit psql
\q
```

### 2. Import the Database Dump

```bash
# Import the dump file
psql -h localhost -U mc -d klikk_bi_v3 -f database_dump.sql

# Or if you need to specify password via environment variable:
PGPASSWORD='Number55dip' psql -h localhost -U mc -d klikk_bi_v3 -f database_dump.sql
```

### 3. Verify the Import

```bash
# Connect to the database
psql -h localhost -U mc -d klikk_bi_v3

# Check tables
\dt

# Check a few records
SELECT COUNT(*) FROM django_migrations;
SELECT COUNT(*) FROM user_user;

# Exit
\q
```

## Notes

- The dump file was created with `--clean --if-exists` flags, which means it includes DROP statements. This is safe for a fresh database.
- The dump includes `--no-owner --no-acl` flags, so it won't try to set ownership or access control lists that might not exist on the server.
- Make sure to update the database credentials in `settings.py` to match your server configuration.
- The dump file is approximately 162MB in size.

## Troubleshooting

### Permission Errors
If you encounter permission errors, ensure the database user has the necessary privileges:
```sql
ALTER USER mc CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE klikk_bi_v3 TO mc;
```

### Connection Errors
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check PostgreSQL is listening on the correct port: `sudo netstat -tlnp | grep 5432`
- Verify firewall rules allow connections

### Import Errors
- Check PostgreSQL version compatibility (dump was created with PostgreSQL 15.10)
- Ensure sufficient disk space
- Check PostgreSQL logs for detailed error messages
