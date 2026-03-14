#!/bin/bash
# Restart gunicorn service
# Usage: ./restart.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="klikk-financials"

echo -e "${BLUE}Restarting $SERVICE_NAME...${NC}"
echo ""

# Check if service exists
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo -e "${RED}Error: Service $SERVICE_NAME not found${NC}"
    exit 1
fi

# Restart service
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Stopping service...${NC}"
    sudo systemctl stop "$SERVICE_NAME"
    sleep 2
fi

echo -e "${YELLOW}Starting service...${NC}"
sudo systemctl start "$SERVICE_NAME"
sleep 2

# Check status
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${GREEN}✓ Service restarted successfully${NC}"
    echo ""
    systemctl status "$SERVICE_NAME" --no-pager -l | head -10
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo ""
    echo "Check logs:"
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    exit 1
fi
