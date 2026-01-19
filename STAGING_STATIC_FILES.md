# Staging Static Files Setup

## Problem
Static files are not being served in staging because `DEBUG=False` and static files configuration was missing.

## Solution Applied

1. **Added static files configuration to `staging.py`:**
   - `STATIC_URL = '/static/'`
   - `STATIC_ROOT = BASE_DIR / 'staticfiles'`
   - `MEDIA_URL = '/media/'`
   - `MEDIA_ROOT = BASE_DIR / 'media'`

2. **Updated `urls.py` to serve static files:**
   - Added static file serving even when `DEBUG=False` for staging convenience

3. **Fixed `DEBUG` setting:**
   - Changed from `DEBUG = True` to `DEBUG = False` in staging settings

## Steps to Deploy on Staging Server

### 1. Collect Static Files

On your staging VM, run:
```bash
# Make sure you're using staging settings
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging

# Collect all static files into the staticfiles directory
python manage.py collectstatic --noinput
```

This will:
- Collect all static files from all apps
- Copy them to `staticfiles/` directory
- Make them available at `/static/` URL

### 2. Verify Static Files Directory

Check that the directory was created:
```bash
ls -la staticfiles/
```

### 3. Set Permissions (if needed)

Make sure the web server can read the files:
```bash
chmod -R 755 staticfiles/
```

### 4. Restart Your Server

Restart your Django application server (gunicorn, uwsgi, or runserver):
```bash
# If using runserver
python manage.py runserver 0.0.0.0:8000

# If using gunicorn
gunicorn klikk_business_intelligence.wsgi:application --bind 0.0.0.0:8000

# If using systemd service, restart it
sudo systemctl restart your-django-service
```

### 5. Test Static Files

Visit your staging server and check if static files load:
- `http://192.168.1.236:8000/static/admin/css/base.css` (should load)
- `http://192.168.1.236:8000/admin/` (admin interface should have styles)

## Alternative: Use WhiteNoise (Recommended for Production)

For better performance in production, consider using WhiteNoise:

1. **Install WhiteNoise:**
   ```bash
   pip install whitenoise
   ```

2. **Add to requirements.txt:**
   ```
   whitenoise>=6.0.0
   ```

3. **Update `base.py` middleware:**
   ```python
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
       'django.contrib.sessions.middleware.SessionMiddleware',
       # ... rest of middleware
   ]
   ```

4. **Add to staging.py:**
   ```python
   # WhiteNoise configuration
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```

5. **Run collectstatic:**
   ```bash
   python manage.py collectstatic --noinput
   ```

WhiteNoise will serve static files efficiently without needing a separate web server.

## Troubleshooting

### Static files still not loading?

1. **Check STATIC_ROOT exists:**
   ```bash
   ls -la staticfiles/
   ```

2. **Verify collectstatic ran successfully:**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Check URL patterns:**
   - Visit: `http://192.168.1.236:8000/static/admin/css/base.css`
   - Should return the CSS file, not a 404

4. **Check server logs:**
   - Look for any errors related to static files

5. **Verify settings are loaded:**
   ```bash
   python manage.py shell -c "from django.conf import settings; print(f'STATIC_ROOT: {settings.STATIC_ROOT}'); print(f'STATIC_URL: {settings.STATIC_URL}')"
   ```

### Permission Errors?

```bash
# Make sure the directory is writable
chmod -R 755 staticfiles/
chown -R your-user:your-group staticfiles/
```

## Notes

- Static files are now served via Django URL patterns (works for staging)
- For production, consider using nginx/Apache or WhiteNoise for better performance
- Media files (user uploads) are served at `/media/` if configured
