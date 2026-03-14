#!/bin/bash
# Backup PostgreSQL database
# Usage: ./backup_db.sh [backup_name]

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DB_NAME="klikk_financials"
DB_USER="klikk_user"
BACKUP_DIR="/home/mc/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${1:-backup_${DATE}}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Database Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if PostgreSQL is running
if ! pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to PostgreSQL database${NC}"
    exit 1
fi

echo -e "${YELLOW}Backing up database: $DB_NAME${NC}"
echo "Backup file: $BACKUP_FILE"
echo ""

# Perform backup
if PGPASSWORD="${DB_PASSWORD:-StrongPasswordHere}" pg_dump -U "$DB_USER" -h localhost "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
    # Compress backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    echo "File: $BACKUP_FILE"
    echo "Size: $SIZE"
    echo ""
    
    # List recent backups
    echo -e "${BLUE}Recent backups:${NC}"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5 || echo "No previous backups found"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi
