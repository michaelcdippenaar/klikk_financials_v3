# SSH Configuration for Staging Server

## Quick Connection

You can now connect to your staging server using the saved terminal profile:

1. **Open Terminal Panel**: `Ctrl+` ` (or Cmd+` on Mac)
2. **Click the dropdown** next to the `+` button
3. **Select "SSH Staging Server"**

Or use the keyboard shortcut:
- Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
- Type "Terminal: Select Default Profile"
- Choose "SSH Staging Server"

## SSH Config File (Optional)

For even easier connection, you can add this to your `~/.ssh/config` file:

```bash
# Add to ~/.ssh/config
Host staging
    HostName 192.168.1.236
    User mc
    IdentityFile ~/.ssh/id_rsa  # Optional: specify your SSH key
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Then you can simply connect with:
```bash
ssh staging
```

## Terminal Profiles Available

1. **SSH Staging Server**: Basic SSH connection
2. **SSH Staging Server (with auto-cd)**: Automatically changes to project directory after connection

## VS Code Tasks

You can also run tasks to open SSH connections:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P`)
2. Type "Tasks: Run Task"
3. Select:
   - "SSH: Connect to Staging Server"
   - "SSH: Connect to Staging Server (Auto CD)"

## Quick Commands After Connection

Once connected, useful commands:

```bash
# Check gunicorn logs
sudo journalctl -u klikk-financials -f

# Check service status
sudo systemctl status klikk-financials

# Restart service
sudo systemctl restart klikk-financials

# Navigate to project
cd /home/mc/apps/klikk_financials_v3

# Check deployment script
bash scripts/check_logs.sh
```
