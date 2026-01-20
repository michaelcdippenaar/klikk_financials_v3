# Installing Server Scripts

## Quick Install (from local machine)

Run the copy script from your local machine:

```bash
cd /path/to/klikk_financials_v3/scripts/server
./copy_to_server.sh
```

## Manual Install

### Step 1: Copy Scripts

From your local machine:

```bash
# Copy all scripts
scp scripts/server/*.sh mc@192.168.1.236:/home/mc/apps/klikk_financials_v3/scripts/server/

# Or copy entire directory
scp -r scripts/server mc@192.168.1.236:/home/mc/apps/klikk_financials_v3/scripts/
```

### Step 2: Make Executable

SSH into your server:

```bash
ssh mc@192.168.1.236
cd /home/mc/apps/klikk_financials_v3/scripts/server
chmod +x *.sh
```

### Step 3: Verify

Test that scripts work:

```bash
./status.sh
```

## Directory Structure on Server

After installation, your server should have:

```
/home/mc/apps/klikk_financials_v3/
├── scripts/
│   └── server/
│       ├── deploy.sh
│       ├── update.sh
│       ├── restart.sh
│       ├── status.sh
│       ├── logs.sh
│       ├── backup_db.sh
│       └── README.md
```

## Usage

Once installed, you can use the scripts from anywhere on the server:

```bash
# From project root
cd /home/mc/apps/klikk_financials_v3
./scripts/server/deploy.sh

# Or from scripts/server directory
cd /home/mc/apps/klikk_financials_v3/scripts/server
./deploy.sh
```

## Updating Scripts

To update scripts after making changes:

```bash
# From local machine
./copy_to_server.sh

# Or manually
scp scripts/server/*.sh mc@192.168.1.236:/home/mc/apps/klikk_financials_v3/scripts/server/
```
