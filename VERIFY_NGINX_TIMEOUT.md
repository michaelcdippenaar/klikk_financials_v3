# Verify Nginx Timeout Settings

## Quick Verification Commands

Run these commands on your Ubuntu server to verify the timeout settings are correctly configured:

### 1. Check if timeout settings are in your nginx config:

```bash
# Find your nginx site config file
sudo grep -r "proxy_read_timeout" /etc/nginx/sites-available/

# Or check the main config
sudo grep "proxy_read_timeout" /etc/nginx/nginx.conf

# Check all timeout-related settings
sudo grep -E "proxy_(read|send|connect)_timeout|send_timeout" /etc/nginx/sites-available/*
```

### 2. View your actual nginx configuration:

```bash
# List all site configs
ls -la /etc/nginx/sites-available/

# View your config (replace with your actual config filename)
sudo cat /etc/nginx/sites-available/klikk-financials
# or
sudo cat /etc/nginx/sites-available/default
```

### 3. What to look for:

Your `location /` block should contain these lines:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    # ... other proxy settings ...
    
    # These timeout settings MUST be present:
    proxy_read_timeout 1800s;
    proxy_send_timeout 1800s;
    proxy_connect_timeout 1800s;
    send_timeout 1800s;
}
```

### 4. Test the endpoint again:

After confirming the settings are in place, test your endpoint:

```bash
curl -X POST http://192.168.1.236/xero/data/update/journals/ \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "your-tenant-id", "load_all": true}' \
  --max-time 2000
```

If it still times out after 60 seconds, the timeout settings might not be in the correct location or nginx might be using a different config file.

### 5. Check which config file nginx is actually using:

```bash
# See which config files nginx is using
sudo nginx -T 2>/dev/null | grep -A 20 "location /"

# Or check the main config
sudo nginx -T 2>/dev/null | grep "proxy_read_timeout"
```

### 6. If timeout settings are missing:

If the grep commands don't find `proxy_read_timeout`, you need to add them:

```bash
# Edit your nginx config
sudo nano /etc/nginx/sites-available/klikk-financials
# (or whatever your config file is named)

# Add these lines inside the location / block:
#     proxy_read_timeout 1800s;
#     proxy_send_timeout 1800s;
#     proxy_connect_timeout 1800s;
#     send_timeout 1800s;

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## Expected Output

When you run `sudo grep "proxy_read_timeout" /etc/nginx/sites-available/*`, you should see:

```
/etc/nginx/sites-available/klikk-financials:    proxy_read_timeout 1800s;
```

If you see nothing, the timeout settings are not configured yet.
