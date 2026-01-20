# Automatic Deployment Setup

This guide explains how to set up automatic deployment from GitHub to the staging server using webhooks.

## Overview

When you push commits to the `main` branch on GitHub, a webhook will automatically:
1. Pull the latest code
2. Install/update dependencies if `requirements.txt` changed
3. Run migrations if new migrations exist
4. Collect static files
5. Restart the gunicorn service

## Prerequisites

- GitHub repository with webhook support
- Staging server accessible from the internet (or GitHub webhook accessible)
- Django app running on staging server
- Systemd service configured for gunicorn

## Setup Instructions

### Step 1: Generate Webhook Secret

On your staging server, generate a secure secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save this secret - you'll need it for both GitHub and the server.

### Step 2: Configure Server Environment Variable

On your staging server, add the webhook secret to your environment:

```bash
# Add to your systemd service environment file or .env
export GITHUB_WEBHOOK_SECRET="your-generated-secret-here"
```

**For systemd service**, edit `/etc/systemd/system/klikk-financials.service`:

```ini
[Service]
Environment="GITHUB_WEBHOOK_SECRET=your-generated-secret-here"
# ... other environment variables
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart klikk-financials
```

### Step 3: Make Deploy Script Executable

On your staging server:

```bash
cd /home/mc/apps/klikk_financials_v3
chmod +x scripts/deploy.sh
```

### Step 4: Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure the webhook:
   - **Payload URL**: `http://your-server-ip:8000/deployment/webhook/github/`
     - Or if using a domain: `https://your-domain.com/deployment/webhook/github/`
   - **Content type**: `application/json`
   - **Secret**: Paste the secret you generated in Step 1
   - **Which events**: Select "Just the push event"
   - **Active**: ✓ (checked)
4. Click **Add webhook**

### Step 5: Test the Webhook

1. Make a small change to your code (e.g., add a comment)
2. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "Test webhook deployment"
   git push origin main
   ```
3. Check the webhook delivery:
   - Go to GitHub → Settings → Webhooks → Your webhook
   - Click on "Recent Deliveries"
   - You should see a successful delivery (green checkmark)
4. Check server logs:
   ```bash
   # Check webhook endpoint logs
   sudo journalctl -u klikk-financials -f | grep -i webhook
   
   # Check deployment script output
   sudo journalctl -u klikk-financials -f | grep -i deploy
   ```

### Step 6: Verify Deployment

After pushing, verify the deployment worked:

```bash
# Check service status
sudo systemctl status klikk-financials

# Check recent commits
cd /home/mc/apps/klikk_financials_v3
git log --oneline -5

# Check if code was updated
git status
```

## Security Considerations

### Webhook Secret

- **Always use a strong, random secret** (at least 32 characters)
- **Never commit the secret to Git**
- **Use environment variables** to store the secret
- The webhook endpoint verifies the signature using HMAC SHA256

### Network Security

- **Use HTTPS** if your server is publicly accessible
- **Consider IP whitelisting** if possible (GitHub webhook IPs)
- **Monitor webhook deliveries** in GitHub for suspicious activity
- **Review logs regularly** for unauthorized access attempts

### Access Control

The webhook endpoint is currently open (`AllowAny` permission). For additional security, you can:

1. **Add IP whitelisting** in Nginx:
   ```nginx
   location /deployment/webhook/github/ {
       allow 140.82.112.0/20;  # GitHub webhook IPs
       allow 192.30.252.0/22;  # GitHub webhook IPs
       deny all;
       proxy_pass http://127.0.0.1:8000;
   }
   ```

2. **Add authentication** to the webhook endpoint (modify `views.py`)

## Troubleshooting

### Webhook Not Triggering

1. **Check webhook URL is accessible:**
   ```bash
   curl -X POST http://your-server-ip:8000/deployment/webhook/github/ \
     -H "Content-Type: application/json" \
     -H "X-Hub-Signature-256: sha256=test" \
     -d '{"ref":"refs/heads/main"}'
   ```

2. **Check GitHub webhook delivery status:**
   - Go to GitHub → Settings → Webhooks → Recent Deliveries
   - Check for error messages

3. **Check server logs:**
   ```bash
   sudo journalctl -u klikk-financials -n 100 | grep -i webhook
   ```

### Deployment Script Fails

1. **Check script permissions:**
   ```bash
   ls -l scripts/deploy.sh
   # Should show: -rwxr-xr-x
   ```

2. **Test script manually:**
   ```bash
   cd /home/mc/apps/klikk_financials_v3
   bash scripts/deploy.sh
   ```

3. **Check for errors:**
   ```bash
   sudo journalctl -u klikk-financials -n 100
   ```

### Signature Verification Fails

1. **Verify secret is set correctly:**
   ```bash
   # Check environment variable
   sudo systemctl show klikk-financials | grep GITHUB_WEBHOOK_SECRET
   ```

2. **Verify secret matches GitHub:**
   - GitHub: Settings → Webhooks → Your webhook → Edit → Secret
   - Server: Check environment variable

3. **Check logs for signature errors:**
   ```bash
   sudo journalctl -u klikk-financials -n 100 | grep -i signature
   ```

## Manual Deployment

If automatic deployment fails, you can deploy manually:

```bash
cd /home/mc/apps/klikk_financials_v3
bash scripts/deploy.sh
```

Or step by step:

```bash
cd /home/mc/apps/klikk_financials_v3
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart klikk-financials
```

## Disabling Automatic Deployment

To temporarily disable automatic deployment:

1. **Disable webhook in GitHub:**
   - Go to Settings → Webhooks → Your webhook
   - Uncheck "Active"
   - Click "Update webhook"

2. **Or remove the webhook secret** (webhook will fail verification but won't deploy)

## Advanced Configuration

### Custom Deployment Script

You can customize `scripts/deploy.sh` to:
- Run tests before deployment
- Send notifications (email, Slack, etc.)
- Create database backups
- Run custom commands

### Multiple Environments

To deploy to different environments based on branch:
- Modify `github_webhook` view to check different branches
- Use different deploy scripts for staging/production
- Set different environment variables per environment

## References

- [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [Systemd Service Configuration](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
