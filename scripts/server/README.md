# Server Management Scripts

This directory contains scripts for managing the Klikk Financials staging server.

## Installation

Copy all scripts to your server:

```bash
# On your local machine
scp scripts/server/*.sh mc@192.168.1.236:/home/mc/apps/klikk_financials_v3/scripts/server/

# On the server, make scripts executable
cd /home/mc/apps/klikk_financials_v3/scripts/server
chmod +x *.sh
```

## Available Scripts

### 1. `deploy.sh` - Full Deployment
Performs a complete deployment:
- Pulls latest code from GitHub
- Updates dependencies if needed
- Runs migrations if needed
- Collects static files
- Restarts gunicorn service

**Usage:**
```bash
./deploy.sh
```

### 2. `update.sh` - Code Update Only
Updates code from GitHub without running migrations or restarting services.

**Usage:**
```bash
./update.sh [branch]  # Default: main
```

### 3. `restart.sh` - Restart Service
Restarts the gunicorn service.

**Usage:**
```bash
./restart.sh
```

### 4. `status.sh` - Check Server Status
Shows comprehensive server status:
- Service status
- Git status
- Database connection
- Disk and memory usage
- Recent logs

**Usage:**
```bash
./status.sh
```

### 5. `logs.sh` - View Logs
Views gunicorn logs in real-time.

**Usage:**
```bash
./logs.sh              # Follow logs (default)
./logs.sh -n 100        # Show last 100 lines then follow
./logs.sh -e            # Show only errors
./logs.sh -n 50 -e      # Show last 50 error lines
```

### 6. `errors.sh` - View Errors Only
Shows only error messages and exceptions from logs.

**Usage:**
```bash
./errors.sh             # Follow errors (default)
./errors.sh -n 200      # Show last 200 error lines
./errors.sh -a           # Show all errors (no follow)
```

### 7. `traceback.sh` - Full Error Details
Shows complete error tracebacks and stack traces.

**Usage:**
```bash
./traceback.sh          # Shows full error details from recent logs
```

### 8. `backup_db.sh` - Database Backup
Creates a PostgreSQL database backup.

**Usage:**
```bash
./backup_db.sh                    # Auto-named backup
./backup_db.sh my_backup_name     # Custom name
```

Backups are saved to `/home/mc/backups/` and compressed with gzip.

## Quick Reference

```bash
# Full deployment
./deploy.sh

# Quick update (code only)
./update.sh

# Check status
./status.sh

# View logs
./logs.sh

# View errors only
./errors.sh

# View full error traceback
./traceback.sh

# Restart service
./restart.sh

# Backup database
./backup_db.sh
```

## Configuration

Some scripts use these default values (edit scripts to change):
- **Service name**: `klikk-financials`
- **Database name**: `klikk_financials`
- **Database user**: `klikk_user`
- **Backup directory**: `/home/mc/backups`
- **Project directory**: Auto-detected from script location

## Troubleshooting

### Scripts not executable
```bash
chmod +x *.sh
```

### Permission denied
Some scripts require sudo for systemctl commands. Make sure your user has sudo access.

### Service not found
Check that the systemd service is installed:
```bash
sudo systemctl list-unit-files | grep klikk-financials
```

### Database backup fails
Ensure PostgreSQL is running and credentials are correct:
```bash
pg_isready -U klikk_user -d klikk_financials
```

## Integration with GitHub Webhook

The `deploy.sh` script is automatically called by the GitHub webhook when you push to the main branch. You can also run it manually anytime.
