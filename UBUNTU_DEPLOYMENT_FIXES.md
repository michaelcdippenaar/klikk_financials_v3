# Ubuntu Server Deployment Fixes

## Issues Fixed

### 1. Database Connection Error: "connection already closed"

**Problem:** Gunicorn workers were sharing database connections, causing connection errors.

**Solution:** Set `CONN_MAX_AGE = 0` in staging settings to disable connection pooling. Each gunicorn worker now manages its own connections.

### 2. Google Cloud Credentials File Not Found

**Problem:** Hardcoded Mac path `/Users/mcdippenaar/development/...` doesn't exist on Ubuntu server.

**Solution:** Use environment variable `GOOGLE_APPLICATION_CREDENTIALS` to specify the credentials file path.

## Deployment Steps on Ubuntu Server

### Step 1: Upload Google Cloud Credentials File

1. **Create credentials directory:**
   ```bash
   mkdir -p /home/mc/apps/klikk_financials_v3/credentials
   ```

2. **Upload your credentials file:**
   ```bash
   # From your local machine, use scp:
   scp klick-financials01-81b1aeed281d.json mc@192.168.1.236:/home/mc/apps/klikk_financials_v3/credentials/
   ```

3. **Set secure permissions:**
   ```bash
   chmod 600 /home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
   chown mc:mc /home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
   ```

### Step 2: Set Environment Variables

Add to your gunicorn service file or `.env` file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
```

**If using systemd service**, edit `/etc/systemd/system/klikk-financials.service`:

```ini
[Unit]
Description=Klikk Financials Gunicorn
After=network.target

[Service]
User=mc
Group=mc
WorkingDirectory=/home/mc/apps/klikk_financials_v3
Environment="PATH=/home/mc/apps/klikk_financials_v3/venv/bin"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json"
Environment="DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging"
ExecStart=/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:8000 \
    --timeout 3600 \
    --graceful-timeout 3600 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --log-level info \
    klikk_business_intelligence.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Note:** Logs are automatically captured by systemd/journalctl. No need for `--access-logfile` or `--error-logfile` options. View logs with `sudo journalctl -u klikk-financials -f`.

If you prefer log files, see `GUNICORN_LOG_SETUP.md` for setup instructions.

### Step 3: Update Code on Server

```bash
cd /home/mc/apps/klikk_financials_v3
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

### Step 4: Restart Gunicorn Service

```bash
# If using systemd
sudo systemctl daemon-reload
sudo systemctl restart klikk-financials
sudo systemctl status klikk-financials

# Or if running manually (without sudo - recommended for testing)
pkill gunicorn
cd /home/mc/apps/klikk_financials_v3
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=/home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
./venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 --timeout 3600 --graceful-timeout 3600 klikk_business_intelligence.wsgi:application

# Or with sudo (using full path if needed)
# sudo /home/mc/apps/klikk_financials_v3/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 --timeout 3600 --graceful-timeout 3600 klikk_business_intelligence.wsgi:application
```

### Step 5: Verify Fixes

1. **Check logs:**
   ```bash
   # If using systemd service (recommended):
   sudo journalctl -u klikk-financials -f
   
   # Or if using manual gunicorn with log files:
   tail -f /var/log/gunicorn/error.log
   # Or if logging to project directory:
   tail -f /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log
   ```

2. **Test database connection:**
   ```bash
   python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection OK')"
   ```

3. **Test Google credentials:**
   ```bash
   python manage.py shell -c "from apps.xero.xero_integration.services import get_google_credentials; creds = get_google_credentials(); print('Google credentials OK')"
   ```

## Gunicorn Configuration Recommendations

For better stability with database connections:

**First, create log directory (if using log files):**
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown mc:mc /var/log/gunicorn
```

**Recommended gunicorn command (use full path from virtual environment):**

```bash
# Option 1: With log files (requires log directory setup above)
/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 3600 \
    --graceful-timeout 3600 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --bind 0.0.0.0:8000 \
    --log-level info \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    klikk_business_intelligence.wsgi:application

# Option 2: Without log files (logs to stdout/stderr, captured by systemd/journalctl)
/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 3600 \
    --graceful-timeout 3600 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --bind 0.0.0.0:8000 \
    --log-level info \
    klikk_business_intelligence.wsgi:application

# Option 3: Log to project directory (no sudo needed)
/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 3600 \
    --graceful-timeout 3600 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --bind 0.0.0.0:8000 \
    --log-level info \
    --access-logfile /home/mc/apps/klikk_financials_v3/logs/gunicorn-access.log \
    --error-logfile /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log \
    klikk_business_intelligence.wsgi:application
```

**Note:** For systemd service, logs go to journalctl by default, so log file options are optional.

**Key settings:**
- `--workers 3`: Number of worker processes (adjust based on CPU cores)
- `--max-requests 1000`: Restart workers after 1000 requests (prevents memory leaks)
- `--max-requests-jitter 50`: Randomize restart to avoid all workers restarting at once
- `--timeout 3600`: Request timeout in seconds (60 minutes for very large datasets with 20k+ records)
- `--graceful-timeout 3600`: Graceful shutdown timeout (allows workers to finish current requests)

## Troubleshooting

### Still getting "connection already closed" errors?

1. **Reduce CONN_MAX_AGE to 0** (already done in staging.py)
2. **Restart gunicorn workers more frequently:**
   ```bash
   --max-requests 500  # Restart workers more often
   ```
3. **Check PostgreSQL max_connections:**
   ```sql
   SHOW max_connections;
   ```
   Make sure it's higher than (gunicorn_workers × 2)

### Google credentials still not found?

1. **Verify file exists:**
   ```bash
   ls -la /home/mc/apps/klikk_financials_v3/credentials/
   ```

2. **Check environment variable:**
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

3. **Test in Python:**
   ```bash
   python -c "import os; print(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))"
   ```

4. **Check file permissions:**
   ```bash
   ls -la /home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
   ```

### Python version warning?

The warning about Python 3.10.12 is just informational. Consider upgrading to Python 3.11+ in the future, but it won't affect functionality now.

## Security Notes

- **Never commit credentials files to git**
- **Use environment variables for sensitive paths**
- **Set file permissions to 600 (read/write for owner only)**
- **Consider using a secrets manager for production**
