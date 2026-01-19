# Settings Configuration Guide

This project uses environment-specific settings files to manage different configurations for development, staging, and production environments.

## Settings Structure

```
klikk_business_intelligence/
├── settings.py                    # Main settings file (imports from settings package)
└── settings/
    ├── __init__.py                # Settings package initialization
    ├── base.py                    # Common settings shared across all environments
    ├── development.py             # Development environment settings
    ├── staging.py                 # Staging environment settings
    └── production.py              # Production environment settings
```

## Environment Configuration

### Development Environment

**Default settings** - Used when no environment is specified.

- **Database**: `klikk_financials`
- **User**: `klikk_user`
- **Password**: `StrongPasswordHere`
- **Host**: `127.0.0.1`
- **Port**: `5432`
- **DEBUG**: `True`
- **Scheduler**: Disabled

**Usage:**
```bash
# Default (development)
python manage.py runserver

# Explicitly set development
export DJANGO_ENV=development
python manage.py runserver
```

### Staging Environment

- **Database**: `klikk_financials`
- **User**: `klikk_user`
- **Password**: `StrongPasswordHere`
- **Host**: `127.0.0.1`
- **Port**: `5432`
- **DEBUG**: `False`
- **Scheduler**: Enabled

**Usage:**
```bash
export DJANGO_ENV=staging
python manage.py runserver

# Or set DJANGO_SETTINGS_MODULE directly
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
python manage.py runserver
```

**Environment Variables:**
- `DJANGO_SECRET_KEY` - Django secret key (optional, has default)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts (default: localhost)

### Production Environment

- **Database**: Configured via environment variables
- **DEBUG**: `False`
- **Scheduler**: Enabled
- **Security**: Enhanced security settings enabled

**Required Environment Variables:**
```bash
DJANGO_SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=klikk_financials_prod
DB_USER=klikk_user
DB_PASSWORD=your-production-password
DB_HOST=your-db-host
DB_PORT=5432
```

**Usage:**
```bash
export DJANGO_ENV=production
export DJANGO_SECRET_KEY=your-secret-key-here
export ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
export DB_NAME=klikk_financials_prod
export DB_USER=klikk_user
export DB_PASSWORD=your-production-password
export DB_HOST=your-db-host
export DB_PORT=5432

python manage.py runserver

# Or set DJANGO_SETTINGS_MODULE directly
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.production
python manage.py runserver
```

## Using Settings in Different Environments

### Method 1: Using DJANGO_SETTINGS_MODULE (Recommended)

Set the `DJANGO_SETTINGS_MODULE` environment variable directly:
```bash
# Development (default)
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.development
python manage.py runserver

# Staging
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
python manage.py runserver

# Production
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.production
python manage.py runserver
```

### Method 2: Backward Compatibility

The main `settings.py` file imports development settings by default for backward compatibility:
```bash
# Uses development settings
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings
python manage.py runserver
```

### Method 3: In WSGI/ASGI Configuration

Update your `wsgi.py` or `asgi.py`:
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'klikk_business_intelligence.settings.production')
application = get_wsgi_application()
```

## Security Notes

1. **Never commit sensitive values** to version control
2. **Production secrets** should always come from environment variables
3. **Development and staging** use hardcoded values for convenience, but production requires environment variables
4. **Secret keys** should be unique for each environment
5. **Database passwords** in production should be strong and stored securely

## Database Configuration

### Development & Staging
Both use the same database configuration:
- Database: `klikk_financials`
- User: `klikk_user`
- Password: `StrongPasswordHere`
- Host: `127.0.0.1`
- Port: `5432`

### Production
Production database configuration is read from environment variables:
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password (required)
- `DB_HOST` - Database host
- `DB_PORT` - Database port (default: 5432)

## Migration Commands

When running migrations, make sure to set the correct environment:

```bash
# Development
export DJANGO_ENV=development
python manage.py migrate

# Staging
export DJANGO_ENV=staging
python manage.py migrate

# Production
export DJANGO_ENV=production
python manage.py migrate
```

## Troubleshooting

### Settings Import Error
If you get import errors, make sure you're using the correct Python path:
```bash
# From project root
export PYTHONPATH=/path/to/klikk_financials_v3:$PYTHONPATH
```

### Database Connection Errors
- Verify database credentials are correct
- Ensure PostgreSQL is running
- Check firewall rules if connecting to remote database
- Verify database exists: `psql -U klikk_user -d klikk_financials -c "SELECT 1;"`

### Environment Variable Not Found
Production settings will raise errors if required environment variables are missing. Make sure all required variables are set before running the application.
