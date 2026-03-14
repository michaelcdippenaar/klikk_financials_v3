#!/bin/bash
# Automatic deployment script for staging server
# Usage: ./deploy.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="klikk-financials"
BRANCH="main"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Klikk Financials Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    exit 1
fi

# Pull latest code
echo -e "${YELLOW}[1/5] Pulling latest code from GitHub...${NC}"
git fetch origin
git reset --hard origin/$BRANCH
git pull origin $BRANCH

# Check if requirements.txt changed
REQUIREMENTS_CHANGED=$(git diff HEAD@{1} HEAD --name-only 2>/dev/null | grep -c "requirements.txt" || echo "0")
if [ "$REQUIREMENTS_CHANGED" -gt 0 ] || [ ! -f "$VENV_DIR/.requirements_installed" ]; then
    echo -e "${YELLOW}[2/5] Installing/updating dependencies...${NC}"
    pip install -q -r requirements.txt
    touch "$VENV_DIR/.requirements_installed"
else
    echo -e "${GREEN}[2/5] Requirements unchanged, skipping pip install${NC}"
fi

# Check if migrations changed
MIGRATIONS_CHANGED=$(git diff HEAD@{1} HEAD --name-only 2>/dev/null | grep -E "migrations/.*\.py$" | wc -l || echo "0")
if [ "$MIGRATIONS_CHANGED" -gt 0 ]; then
    echo -e "${YELLOW}[3/5] Running database migrations...${NC}"
    python manage.py migrate --noinput
else
    echo -e "${GREEN}[3/5] No new migrations, skipping migrate${NC}"
fi

# Collect static files (always run to ensure they're up to date)
echo -e "${YELLOW}[4/5] Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Restart gunicorn service
echo -e "${YELLOW}[5/5] Restarting gunicorn service...${NC}"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl restart "$SERVICE_NAME"
    echo -e "${GREEN}Service restarted${NC}"
else
    echo -e "${YELLOW}Service not running, starting it...${NC}"
    sudo systemctl start "$SERVICE_NAME"
fi

# Wait a moment for service to start
sleep 2

# Check service status
echo ""
echo -e "${BLUE}========================================${NC}"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
    echo -e "${GREEN}Service status: $(sudo systemctl is-active $SERVICE_NAME)${NC}"
    echo ""
    echo -e "${BLUE}Recent commits:${NC}"
    git log --oneline -5
    exit 0
else
    echo -e "${RED}✗ Deployment completed but service is not running!${NC}"
    echo -e "${YELLOW}Check logs: sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    exit 1
fi
