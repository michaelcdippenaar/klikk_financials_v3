#!/bin/bash
# Copy server scripts to staging server
# Usage: ./copy_to_server.sh

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER="mc@192.168.1.236"
SERVER_DIR="/home/mc/apps/klikk_financials_v3/scripts/server"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}Copying server scripts to staging server...${NC}"
echo "Server: $SERVER"
echo "Destination: $SERVER_DIR"
echo ""

# Create directory on server
ssh "$SERVER" "mkdir -p $SERVER_DIR"

# Copy all scripts
echo -e "${YELLOW}Copying scripts...${NC}"
scp "$LOCAL_DIR"/*.sh "$SERVER:$SERVER_DIR/"

# Make scripts executable
echo -e "${YELLOW}Making scripts executable...${NC}"
ssh "$SERVER" "chmod +x $SERVER_DIR/*.sh"

echo ""
echo -e "${GREEN}✓ Scripts copied successfully!${NC}"
echo ""
echo "You can now use the scripts on the server:"
echo "  ssh $SERVER"
echo "  cd $SERVER_DIR"
echo "  ./deploy.sh"
