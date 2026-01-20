# Fix Nginx 504 Gateway Timeout

## Problem

You're getting a 504 Gateway Timeout from nginx after exactly 60 seconds, even though gunicorn timeout is set higher. This is because **nginx has its own timeout settings** that are separate from gunicorn.

## Solution: Update Nginx Timeout Settings

### Step 1: Find Your Nginx Configuration File

On your Ubuntu server, find your nginx site configuration:

```bash
# Usually located at:
/etc/nginx/sites-available/klikk-financials
# or
/etc/nginx/sites-available/default
# or
/etc/nginx/nginx.conf
```

### Step 2: Update Nginx Configuration

Edit your nginx configuration file and add/increase these timeout settings:

```nginx
server {
    listen 80;
    server_name 192.168.1.236;  # or your domain name

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CRITICAL: Increase timeouts for long-running operations
        # Default is 60 seconds - increase to 30 minutes for large datasets
        proxy_connect_timeout 1800s;
        proxy_send_timeout 1800s;
        proxy_read_timeout 1800s;
        send_timeout 1800s;
        
        # Optional: Increase buffer sizes for large responses
        proxy_buffering off;  # Disable buffering for streaming responses
        # OR if you need buffering:
        # proxy_buffer_size 128k;
        # proxy_buffers 4 256k;
        # proxy_busy_buffers_size 256k;
    }
}
```

### Step 3: Test and Reload Nginx

```bash
# Test nginx configuration for syntax errors
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx

# Or restart nginx
sudo systemctl restart nginx
```

### Step 4: Verify Settings

Check that nginx is using the new configuration:

```bash
# Check nginx status
sudo systemctl status nginx

# View nginx error logs if issues persist
sudo tail -f /var/log/nginx/error.log
```

## Complete Example Configuration

Here's a complete nginx configuration example:

```nginx
upstream gunicorn {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name 192.168.1.236;

    client_max_body_size 100M;

    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings for long-running operations
        proxy_connect_timeout 1800s;
        proxy_send_timeout 1800s;
        proxy_read_timeout 1800s;
        send_timeout 1800s;
        
        # Disable buffering for real-time responses
        proxy_buffering off;
    }

    # Static files (if serving directly from nginx)
    location /static/ {
        alias /home/mc/apps/klikk_financials_v3/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if serving directly from nginx)
    location /media/ {
        alias /home/mc/apps/klikk_financials_v3/media/;
    }
}
```

## Timeout Values Explained

- **proxy_connect_timeout**: Time to establish connection to backend (1800s = 30 minutes)
- **proxy_send_timeout**: Time to send request to backend (1800s = 30 minutes)
- **proxy_read_timeout**: Time to wait for response from backend (1800s = 30 minutes) - **THIS IS THE KEY ONE**
- **send_timeout**: Time to send response to client (1800s = 30 minutes)

## For Very Large Operations (20k+ records)

If you're processing 20,000+ records and need even more time:

```nginx
# Increase to 60 minutes (3600 seconds)
proxy_connect_timeout 3600s;
proxy_send_timeout 3600s;
proxy_read_timeout 3600s;
send_timeout 3600s;
```

## Troubleshooting

### Still getting 504 after updating nginx?

1. **Verify nginx configuration is loaded:**
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

2. **Check nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Verify gunicorn timeout is also increased:**
   ```bash
   # Check your systemd service file
   cat /etc/systemd/system/klikk-financials.service | grep timeout
   # Should show: --timeout 1800
   ```

4. **Check if there's a load balancer in front:**
   - If using a cloud load balancer (AWS ALB, GCP LB, etc.), update its timeout settings too

### Operation completes but still times out?

This might be a client-side timeout (browser, Postman, curl). Increase client timeout:

```bash
# For curl, use --max-time
curl --max-time 1800 -X POST http://192.168.1.236/xero/data/update/journals/ \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "your-tenant-id", "load_all": true}'
```

## Quick Fix Command

If you just want to quickly update the timeout in your existing nginx config:

```bash
# Backup current config
sudo cp /etc/nginx/sites-available/klikk-financials /etc/nginx/sites-available/klikk-financials.backup

# Edit the file
sudo nano /etc/nginx/sites-available/klikk-financials

# Add these lines inside the location / block:
#     proxy_read_timeout 1800s;
#     proxy_send_timeout 1800s;
#     proxy_connect_timeout 1800s;
#     send_timeout 1800s;

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## Notes

- **nginx timeout must be >= gunicorn timeout** for long operations
- **Default nginx timeout is 60 seconds** - this is why you're seeing the 1-minute timeout
- **After updating nginx, you must reload/restart** for changes to take effect
- **Monitor nginx logs** to see if there are other issues
