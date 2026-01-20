#!/bin/bash
# Automatic deployment script for staging server
# This script is triggered by GitHub webhook

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/mc/apps/klikk_financials_v3"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="klikk-financials"
BRANCH="main"

echo -e "${GREEN}Starting deployment...${NC}"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Pull latest code
echo -e "${YELLOW}Pulling latest code from GitHub...${NC}"
git fetch origin
git reset --hard origin/$BRANCH
git pull origin $BRANCH

# Check if requirements.txt changed
REQUIREMENTS_CHANGED=$(git diff HEAD@{1} HEAD --name-only | grep -c "requirements.txt" || true)
if [ "$REQUIREMENTS_CHANGED" -gt 0 ] || [ ! -f "$VENV_DIR/.requirements_installed" ]; then
    echo -e "${YELLOW}Installing/updating dependencies...${NC}"
    pip install -q -r requirements.txt
    touch "$VENV_DIR/.requirements_installed"
else
    echo -e "${GREEN}Requirements unchanged, skipping pip install${NC}"
fi

# Check if migrations changed
MIGRATIONS_CHANGED=$(git diff HEAD@{1} HEAD --name-only | grep -E "migrations/.*\.py$" | wc -l || true)
if [ "$MIGRATIONS_CHANGED" -gt 0 ]; then
    echo -e "${YELLOW}Running database migrations...${NC}"
    python manage.py migrate --noinput
else
    echo -e "${GREEN}No new migrations, skipping migrate${NC}"
fi

# Collect static files (always run to ensure they're up to date)
echo -e "${YELLOW}Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Restart gunicorn service
echo -e "${YELLOW}Restarting gunicorn service...${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
    echo -e "${GREEN}Service restarted${NC}"
else
    echo -e "${YELLOW}Service not running, starting it...${NC}"
    sudo systemctl start "$SERVICE_NAME"
fi

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
    echo -e "${GREEN}Service status: $(sudo systemctl is-active $SERVICE_NAME)${NC}"
    exit 0
else
    echo -e "${RED}✗ Deployment completed but service is not running!${NC}"
    echo -e "${YELLOW}Check logs: sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    exit 1
fi
