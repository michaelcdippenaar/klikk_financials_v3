#!/bin/bash
# Update code from GitHub (without full deployment)
# Usage: ./update.sh [branch]

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BRANCH="${1:-main}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Code Update${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_DIR" || exit 1

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    echo "Stashing changes..."
    git stash
fi

# Fetch and pull
echo -e "${YELLOW}Pulling latest code from branch: $BRANCH${NC}"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo ""
echo -e "${GREEN}✓ Code updated successfully${NC}"
echo ""
echo -e "${BLUE}Recent commits:${NC}"
git log --oneline -5

echo ""
echo -e "${YELLOW}Note: Run ./deploy.sh for full deployment${NC}"
