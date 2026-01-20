# Gunicorn Log File Setup

## Problem

Gunicorn fails with error: `'/var/log/gunicorn/error.log' isn't writable [FileNotFoundError(2, 'No such file or directory')]`

This happens because the log directory doesn't exist or the user doesn't have permission to write to it.

## Solutions

### Option 1: Create Log Directory (Recommended for Production)

```bash
# Create the log directory
sudo mkdir -p /var/log/gunicorn

# Set ownership to your user
sudo chown mc:mc /var/log/gunicorn

# Set permissions
sudo chmod 755 /var/log/gunicorn
```

Then gunicorn can write logs to `/var/log/gunicorn/access.log` and `/var/log/gunicorn/error.log`.

### Option 2: Use Project Directory for Logs (Easier, No Sudo Needed)

Create a logs directory in your project:

```bash
cd /home/mc/apps/klikk_financials_v3
mkdir -p logs
chmod 755 logs
```

Then use these log paths in gunicorn:
```bash
--access-logfile /home/mc/apps/klikk_financials_v3/logs/gunicorn-access.log
--error-logfile /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log
```

### Option 3: Don't Use Log Files (Use systemd/journalctl)

If using systemd service, you don't need log files - logs go to journalctl automatically. Just remove the `--access-logfile` and `--error-logfile` options:

```bash
/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:8000 \
    --timeout 3600 \
    --graceful-timeout 3600 \
    --log-level info \
    klikk_business_intelligence.wsgi:application
```

Then view logs with:
```bash
sudo journalctl -u klikk-financials -f
```

## Recommended Approach

**For systemd service:** Use Option 3 (no log files, use journalctl)
- Logs are automatically captured
- No file permission issues
- Easy to view with `journalctl`

**For manual testing:** Use Option 2 (project directory)
- No sudo needed
- Logs are in your project directory
- Easy to find and view

**For production with separate log management:** Use Option 1
- Centralized log location
- Can be managed by log rotation tools
- Requires sudo setup

## Update Systemd Service (if using Option 3)

If you want to remove log files from your systemd service:

```ini
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
```

Remove the `--access-logfile` and `--error-logfile` lines.
