#!/bin/bash
# Quick script to check gunicorn logs live

echo "Checking Gunicorn logs (press Ctrl+C to exit)..."
echo ""

# Check if using systemd service
if systemctl is-active --quiet klikk-financials 2>/dev/null; then
    echo "Using systemd service logs..."
    sudo journalctl -u klikk-financials -f
elif pgrep -f "gunicorn.*klikk_business_intelligence.wsgi" > /dev/null; then
    echo "Gunicorn process found. Checking logs..."
    # If using log files
    if [ -f "/var/log/gunicorn/error.log" ]; then
        echo "Using log file: /var/log/gunicorn/error.log"
        tail -f /var/log/gunicorn/error.log
    elif [ -f "/home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log" ]; then
        echo "Using log file: /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log"
        tail -f /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log
    else
        echo "No log files found. Gunicorn may be logging to stdout/stderr."
        echo "Try: sudo journalctl -u klikk-financials -f"
        echo "Or check the process output directly."
    fi
else
    echo "Gunicorn service not found or not running."
    echo "Check service status: sudo systemctl status klikk-financials"
fi
