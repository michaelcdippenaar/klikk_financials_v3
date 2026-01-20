# Fix Gunicorn Worker Timeout (SystemExit: 1)

## Problem

Gunicorn is killing the worker with `SystemExit: 1` during long-running operations. The error shows:
```
File ".../gunicorn/workers/base.py", line 204, in handle_abort
    sys.exit(1)
SystemExit: 1
```

This happens when gunicorn's timeout is reached, even if you think you've set it.

## Solution: Verify and Fix Gunicorn Timeout

### Step 1: Check Current Gunicorn Configuration

On your Ubuntu server, check if the timeout is actually set:

```bash
# Check your systemd service file
cat /etc/systemd/system/klikk-financials.service

# Check if gunicorn is running with timeout
ps aux | grep gunicorn | grep timeout
```

### Step 2: Update Systemd Service File

Edit the service file:

```bash
sudo nano /etc/systemd/system/klikk-financials.service
```

**Make sure it has `--timeout 3600` (1 hour for 20k+ records):**

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

**Key changes:**
- `--timeout 3600` (60 minutes instead of 30 minutes)
- `--graceful-timeout 3600` (allow graceful shutdown)
- Added `--log-level info` for better debugging

### Step 3: Reload and Restart

```bash
sudo systemctl daemon-reload
sudo systemctl restart klikk-financials
sudo systemctl status klikk-financials
```

### Step 4: Verify Timeout is Applied

```bash
# Check running gunicorn processes
ps aux | grep gunicorn

# You should see --timeout 3600 in the command line
```

### Step 5: Test Again

Try your endpoint again and monitor logs:

```bash
# Watch logs in real-time
sudo journalctl -u klikk-financials -f
```

## Alternative: Increase to 2 Hours

If 1 hour isn't enough for 20,000+ records:

```ini
--timeout 7200 \
--graceful-timeout 7200 \
```

## Why This Happens

1. **Default timeout**: If `--timeout` isn't specified, gunicorn defaults to 30 seconds
2. **Worker abortion**: When timeout is reached, gunicorn sends SIGABRT to the worker
3. **During retries**: The error happens during `time.sleep()` in urllib3's retry logic, which means gunicorn is killing the worker while it's waiting to retry

## Additional Fix: Handle Long Operations Better

Consider making the operation asynchronous or adding progress tracking, but for now, increasing the timeout should allow it to complete.

## Verify All Timeouts Are Set

Make sure you have:

1. ✅ **Gunicorn timeout**: `--timeout 3600` (or higher)
2. ✅ **Nginx timeout**: `proxy_read_timeout 3600s;` (or higher)
3. ✅ **Database timeout**: Removed (no timeout)

## Troubleshooting

### Still getting SystemExit: 1?

1. **Check if timeout is actually in the command:**
   ```bash
   ps aux | grep gunicorn | grep -o "timeout [0-9]*"
   ```

2. **Check systemd logs:**
   ```bash
   sudo journalctl -u klikk-financials | grep -i timeout
   ```

3. **Try running gunicorn manually to test:**
   ```bash
   cd /home/mc/apps/klikk_financials_v3
   source venv/bin/activate
   export GOOGLE_APPLICATION_CREDENTIALS=/home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json
   export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
   ./venv/bin/gunicorn --workers 1 --bind 0.0.0.0:8001 --timeout 3600 --log-level debug klikk_business_intelligence.wsgi:application
   ```
   
   **Note:** Use `./venv/bin/gunicorn` or the full path `/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn` instead of just `gunicorn` since it's installed in the virtual environment.

### Worker keeps restarting?

This might be due to `--max-requests`. For very long operations, you might want to increase it:

```ini
--max-requests 100  # Lower number = restart workers more often (but might interrupt long operations)
```

Or remove it entirely for long-running operations (not recommended for production, but okay for staging).

## Recommended Settings for 20k+ Records

```ini
--timeout 3600              # 60 minutes
--graceful-timeout 3600     # 60 minutes for graceful shutdown
--keep-alive 5              # Keep connections alive
--max-requests 50          # Restart workers after fewer requests to prevent memory leaks
--max-requests-jitter 10   # Randomize restart
```
