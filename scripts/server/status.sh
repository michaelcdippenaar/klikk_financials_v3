#!/bin/bash
# Check server status
# Usage: ./status.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_NAME="klikk-financials"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Server Status Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Service status
echo -e "${YELLOW}Service Status:${NC}"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${GREEN}✓ $SERVICE_NAME is running${NC}"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -5
else
    echo -e "${RED}✗ $SERVICE_NAME is not running${NC}"
fi
echo ""

# Git status
echo -e "${YELLOW}Git Status:${NC}"
cd "$PROJECT_DIR" || exit 1
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"
echo ""

# Database connection
echo -e "${YELLOW}Database Connection:${NC}"
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    python manage.py check --database default 2>&1 | head -3 || echo -e "${RED}Database check failed${NC}"
else
    echo -e "${YELLOW}Virtual environment not found${NC}"
fi
echo ""

# Disk usage
echo -e "${YELLOW}Disk Usage:${NC}"
df -h / | tail -1
echo ""

# Memory usage
echo -e "${YELLOW}Memory Usage:${NC}"
free -h | grep -E "Mem|Swap"
echo ""

# Recent logs
echo -e "${YELLOW}Recent Service Logs (last 5 lines):${NC}"
sudo journalctl -u "$SERVICE_NAME" -n 5 --no-pager 2>/dev/null || echo "No logs available"
echo ""

echo -e "${BLUE}========================================${NC}"
