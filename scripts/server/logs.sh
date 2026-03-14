#!/bin/bash
# View gunicorn logs live
# Usage: ./logs.sh [options]
# Options:
#   -n NUM    Show last N lines before following
#   -e        Show only errors
#   -f        Follow logs (default)

# Colors
RED='\033[0;31m'
GREEN='\033[0;33m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="klikk-financials"
FOLLOW=true
LINES=50
ERRORS_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -e|--errors)
            ERRORS_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -n, --lines NUM    Show last N lines (default: 50)"
            echo "  -e, --errors       Show only errors"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}Checking Gunicorn logs...${NC}"
echo ""

# Check if using systemd service
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${GREEN}Using systemd service logs${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
    echo ""
    
    if [ "$ERRORS_ONLY" = true ]; then
        sudo journalctl -u "$SERVICE_NAME" -n "$LINES" -f | grep -i --color=always "error\|exception\|traceback\|failed"
    else
        sudo journalctl -u "$SERVICE_NAME" -n "$LINES" -f
    fi
elif pgrep -f "gunicorn.*klikk_business_intelligence.wsgi" > /dev/null; then
    echo -e "${GREEN}Gunicorn process found${NC}"
    
    # Check for log files
    if [ -f "/var/log/gunicorn/error.log" ]; then
        echo "Using log file: /var/log/gunicorn/error.log"
        if [ "$ERRORS_ONLY" = true ]; then
            tail -n "$LINES" -f /var/log/gunicorn/error.log | grep -i --color=always "error\|exception\|traceback\|failed"
        else
            tail -n "$LINES" -f /var/log/gunicorn/error.log
        fi
    elif [ -f "/home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log" ]; then
        echo "Using log file: /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log"
        if [ "$ERRORS_ONLY" = true ]; then
            tail -n "$LINES" -f /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log | grep -i --color=always "error\|exception\|traceback\|failed"
        else
            tail -n "$LINES" -f /home/mc/apps/klikk_financials_v3/logs/gunicorn-error.log
        fi
    else
        echo -e "${YELLOW}No log files found. Gunicorn may be logging to stdout/stderr.${NC}"
        echo "Try: sudo journalctl -u $SERVICE_NAME -f"
    fi
else
    echo -e "${RED}Gunicorn service not found or not running.${NC}"
    echo "Check service status: sudo systemctl status $SERVICE_NAME"
    exit 1
fi
