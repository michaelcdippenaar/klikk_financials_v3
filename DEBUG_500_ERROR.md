# Debug 500 Internal Server Error

## Problem

After fixing the nginx timeout, you're now getting a 500 Internal Server Error after ~2 minutes. This indicates an actual application error, not a timeout.

## Step 1: Check Application Logs

On your Ubuntu server, check the logs to see the actual error:

### Check Gunicorn Logs

```bash
# If using systemd service
sudo journalctl -u klikk-financials -n 100 --no-pager

# Or if using manual gunicorn with log files
tail -f /var/log/gunicorn/error.log
tail -f /var/log/gunicorn/access.log
```

### Check Django Logs

```bash
# If you have Django logging configured
tail -f /home/mc/apps/klikk_financials_v3/logs/*.log

# Or check for any log files in the project
find /home/mc/apps/klikk_financials_v3 -name "*.log" -type f
```

### Check Nginx Error Logs

```bash
sudo tail -f /var/log/nginx/error.log
```

## Step 2: Common Causes of 500 Errors After 2 Minutes

### 1. Gunicorn Worker Timeout

Even though you set `--timeout 1800`, check if it's actually being used:

```bash
# Check your systemd service file
cat /etc/systemd/system/klikk-financials.service | grep timeout

# Verify gunicorn is running with the correct timeout
ps aux | grep gunicorn
```

### 2. Database Connection Error

The operation might be losing database connection during long operations:

```bash
# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Or check if PostgreSQL has connection limits
sudo -u postgres psql -c "SHOW max_connections;"
```

### 3. Memory Issues

Large operations might be running out of memory:

```bash
# Check memory usage during the operation
free -h

# Check if any processes were killed (OOM killer)
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
```

### 4. Application Exception

There might be an actual error in the code. Look for Python tracebacks in the logs.

## Step 3: Enable Django Debug Mode Temporarily

**WARNING: Only do this in staging, never in production!**

Temporarily enable DEBUG mode to see the actual error:

```bash
# Edit staging settings
nano /home/mc/apps/klikk_financials_v3/klikk_business_intelligence/settings/staging.py

# Change:
DEBUG = True

# Restart gunicorn
sudo systemctl restart klikk-financials
```

Then try the request again - you'll see the full error traceback in the response.

**Remember to set DEBUG = False again after debugging!**

## Step 4: Check for Specific Errors

### Check if it's a database query timeout:

Look for errors like:
- "connection already closed"
- "server closed the connection unexpectedly"
- "query timeout"

### Check if it's a memory error:

Look for errors like:
- "MemoryError"
- "Killed" (OOM killer)
- "cannot allocate memory"

### Check if it's an application error:

Look for Python tracebacks showing:
- AttributeError
- KeyError
- ValueError
- etc.

## Step 5: Add More Logging

If logs don't show enough detail, add more logging to the journal update function:

```python
# In apps/xero/xero_data/services.py
import logging
logger = logging.getLogger(__name__)

def update_xero_data(tenant_id, user=None, load_all=False):
    logger.info(f"Starting update_xero_data for tenant {tenant_id}, load_all={load_all}")
    # ... existing code ...
    
    try:
        # Add logging at key points
        logger.info("Creating API client...")
        api_client = XeroApiClient(user, tenant_id=tenant_id)
        
        logger.info("Starting journals update...")
        xero_api.journals(load_all=load_all).get()
        logger.info("Journals update completed successfully")
    except Exception as e:
        logger.error(f"Error in update_xero_data: {str(e)}", exc_info=True)
        raise
```

## Quick Diagnostic Commands

Run these to gather information:

```bash
# 1. Check gunicorn process and timeout
ps aux | grep gunicorn | grep -v grep

# 2. Check system resources
free -h
df -h

# 3. Check recent system logs
sudo journalctl -u klikk-financials --since "5 minutes ago" | tail -50

# 4. Check for Python errors
sudo journalctl -u klikk-financials | grep -i "error\|exception\|traceback" | tail -20

# 5. Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'klikk_financials';"
```

## Most Likely Issues

Based on the 2-minute timing:

1. **Gunicorn worker timeout** - Check if `--timeout 1800` is actually set
2. **Database connection timeout** - Connection might be closing during long operation
3. **Memory exhaustion** - Large dataset processing might be using too much memory
4. **Application exception** - An actual error in the code after processing for 2 minutes

## Next Steps

1. **Check the logs first** - This will tell you exactly what's wrong
2. **Share the error message** - Once you see the actual error in logs, we can fix it
3. **Check gunicorn timeout** - Verify it's actually set to 1800 seconds

## Share the Error

Please run:
```bash
sudo journalctl -u klikk-financials -n 100 --no-pager | tail -50
```

And share the output, especially any error messages or tracebacks.
