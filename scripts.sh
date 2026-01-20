#!/bin/bash
# Navigation script to go to project scripts folder
# Place this in the root of your server (e.g., /home/mc/)
# Usage: ./scripts.sh

PROJECT_DIR="/home/mc/apps/klikk_financials_v3"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory not found: $PROJECT_DIR"
    exit 1
fi

# Change to scripts directory
cd "$SCRIPTS_DIR" || exit 1

# Start an interactive shell in the scripts directory
exec $SHELL
