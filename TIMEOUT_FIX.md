# Fix 504 Gateway Timeout for Journal Updates

## Problem

The `xero/data/update/journals/` endpoint is timing out with a 504 Gateway Timeout error when `load_all=true`. This happens because:

1. **Gunicorn timeout is too short**: Currently set to 120 seconds (2 minutes)
2. **Large data operations**: Loading all journals can take 3-5+ minutes depending on data volume
3. **Synchronous operation**: The endpoint blocks until the entire operation completes

## Immediate Fix: Increase Gunicorn Timeout

### Option 1: Update Gunicorn Command (Quick Fix)

Update your gunicorn command or systemd service to increase the timeout:

```bash
gunicorn \
    --workers 3 \
    --worker-class sync \
    --timeout 600 \
    --bind 0.0.0.0:8000 \
    klikk_business_intelligence.wsgi:application
```

**Change:** `--timeout 120` → `--timeout 1800` (30 minutes for large datasets)

### Option 2: Update Systemd Service File

Edit `/etc/systemd/system/klikk-financials.service`:

```ini
[Unit]
Description=Klikk Financials Gunicorn
After=network.target

[Service]
User=mc
Group=mc
WorkingDirectory=/home/mc/apps/klikk_financials_v3
Environment="PATH=/home/mc/apps/klikk_financials_v3/venv/bin"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/mc/apps/klikk_financials_v3/credentials/klick-financials01-81b1aeed281d.json"
Environment="DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging"
ExecStart=/home/mc/apps/klikk_financials_v3/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:8000 \
    --timeout 1800 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    klikk_business_intelligence.wsgi:application

[Install]
WantedBy=multi-user.target
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart klikk-financials
```

### Option 3: Nginx Proxy Timeout (CRITICAL - If using Nginx)

**IMPORTANT:** If you're getting 504 errors after exactly 60 seconds, nginx is timing out!

Nginx has its own timeout settings (default 60 seconds) that are separate from gunicorn. You **MUST** update nginx timeouts.

Edit `/etc/nginx/sites-available/klikk-financials` (or your nginx config file):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CRITICAL: Increase timeouts for long-running operations (30 minutes for 20k+ records)
    # Default nginx timeout is 60 seconds - this is why you see 504 after 1 minute!
    proxy_connect_timeout 1800s;
    proxy_send_timeout 1800s;
    proxy_read_timeout 1800s;  # THIS IS THE KEY ONE
    send_timeout 1800s;
    
    # Optional: Disable buffering for real-time responses
    proxy_buffering off;
}
```

Then reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**See NGINX_TIMEOUT_FIX.md for detailed instructions and troubleshooting.**

## Recommended Timeout Values

- **Small datasets (< 1000 journals)**: 300 seconds (5 minutes)
- **Medium datasets (1000-10000 journals)**: 600 seconds (10 minutes)
- **Large datasets (10000-20000 journals)**: 1800 seconds (30 minutes)
- **Very large datasets (> 20000 journals)**: 3600 seconds (60 minutes)

**For 20,000 records, use at least 1800 seconds (30 minutes) timeout.**

## Long-Term Solution: Asynchronous Processing

For better user experience, consider making the operation asynchronous:

1. **Return immediately** with a task ID
2. **Process in background** using Celery or Django-Q
3. **Provide status endpoint** to check progress
4. **Send notification** when complete

This would require:
- Installing Celery or Django-Q
- Creating a task queue
- Adding a status tracking model
- Updating the endpoint to return task ID immediately

## Testing the Fix

After updating the timeout:

1. **Test with small dataset** (load_all=false):
   ```bash
   curl -X POST http://192.168.1.236:8000/xero/data/update/journals/ \
     -H "Content-Type: application/json" \
     -d '{"tenant_id": "your-tenant-id", "load_all": false}'
   ```

2. **Test with full load** (load_all=true):
   ```bash
   curl -X POST http://192.168.1.236:8000/xero/data/update/journals/ \
     -H "Content-Type: application/json" \
     -d '{"tenant_id": "your-tenant-id", "load_all": true}'
   ```

3. **Monitor logs**:
   ```bash
   sudo journalctl -u klikk-financials -f
   ```

## Troubleshooting

### Still getting timeouts?

1. **Check actual operation time**:
   - Look at logs to see how long the operation actually takes
   - Add timing logs in the service function

2. **Optimize the operation**:
   - Use pagination for large datasets
   - Process in batches (already implemented with 5000 record batches)
   - Add database indexes if needed
   - The code now batches both bulk_create and bulk_update operations

3. **Consider splitting the operation**:
   - Separate endpoint for incremental updates (fast)
   - Separate endpoint for full loads (can be async)

### Operation completes but still times out?

This might be a proxy timeout issue. Check:
- Nginx timeout settings (if using Nginx)
- Load balancer timeout (if using a load balancer)
- Client timeout (browser/Postman timeout)

## Performance Optimizations Applied

The code has been optimized to handle large datasets more efficiently:

1. **Batched bulk_create**: Now processes in batches of 5,000 records (was processing all at once)
2. **Batched bulk_update**: Already processes in batches of 5,000 records
3. **Progress logging**: Added batch-by-batch progress logging for better visibility

This reduces memory usage and database lock contention for large operations.

## Notes

- **Increasing timeout is a quick fix** but not ideal for production
- **Consider rate limiting** to prevent abuse of long-running endpoints
- **Monitor resource usage** - long-running operations consume memory and CPU
- **Set appropriate timeouts** based on your actual data volumes
- **For 20,000+ records**, expect 15-30 minutes processing time depending on:
  - Network speed to Xero API
  - Database performance
  - Server CPU and memory
