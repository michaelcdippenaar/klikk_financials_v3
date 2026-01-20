# Development Environment Setup

## Quick Start

To run the Django server in development mode:

```bash
# Make sure you're in the project directory
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3

# Activate virtual environment (if not already activated)
source .venv/bin/activate

# Run the development server
python manage.py runserver 8005
```

## Development Settings

The development environment uses these database settings:
- **Database**: `klikk_bi_v3`
- **User**: `mc`
- **Password**: `Number55dip`
- **Host**: `127.0.0.1`
- **Port**: `5432`
- **DEBUG**: `True`

## Troubleshooting

### If you get "password authentication failed for user 'klikk_user'"

This means the wrong settings are being loaded. Try:

1. **Explicitly set the settings module:**
   ```bash
   export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.development
   python manage.py runserver 8005
   ```

2. **Or set the environment variable:**
   ```bash
   export DJANGO_ENV=development
   python manage.py runserver 8005
   ```

3. **Clear any cached Python files:**
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
   find . -name "*.pyc" -delete
   ```

### Verify Settings Are Loaded Correctly

Check which settings are being used:
```bash
python manage.py shell -c "from django.conf import settings; print(f'Database: {settings.DATABASES[\"default\"][\"NAME\"]}'); print(f'User: {settings.DATABASES[\"default\"][\"USER\"]}'); print(f'DEBUG: {settings.DEBUG}')"
```

Expected output:
```
Database: klikk_bi_v3
User: mc
DEBUG: True
```

## Common Commands

### Run migrations
```bash
python manage.py migrate
```

### Create superuser
```bash
python manage.py createsuperuser
```

### Run Django shell
```bash
python manage.py shell
```

### Check for issues
```bash
python manage.py check
```

## Environment Variables

You can optionally set these environment variables:

```bash
# Explicitly use development settings
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.development

# Or use the environment variable
export DJANGO_ENV=development
```

## Database Connection Test

Test your database connection:
```bash
python manage.py dbshell
```

Or test with psql directly:
```bash
psql -h 127.0.0.1 -U mc -d klikk_bi_v3
```
