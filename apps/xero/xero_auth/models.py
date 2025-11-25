from django.db import models
from django.conf import settings
from apps.xero.xero_core.models import XeroTenant


class XeroClientCredentials(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='xero_client_credentials', on_delete=models.CASCADE)
    client_id = models.CharField(max_length=100)
    client_secret = models.CharField(max_length=100)
    scope = models.JSONField(blank=True)
    token = models.JSONField(blank=True, null=True)  # Legacy: Store OAuth2 token (deprecated, use tenant_tokens instead)
    refresh_token = models.CharField(max_length=1000, blank=True, null=True)  # Legacy: deprecated, use tenant_tokens instead
    expires_at = models.DateTimeField(blank=True, null=True)  # Legacy: deprecated, use tenant_tokens instead
    tenant_tokens = models.JSONField(default=dict, blank=True)  # Store tenant-specific tokens: {tenant_id: {token, refresh_token, expires_at, connected_at}}
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Credentials for {self.user}"
    
    def get_tenant_token_data(self, tenant_id):
        """Get token data for a specific tenant."""
        return self.tenant_tokens.get(tenant_id)
    
    def set_tenant_token_data(self, tenant_id, token_data, refresh_token=None, expires_at=None, connected_at=None):
        """Set token data for a specific tenant."""
        from django.utils import timezone
        import datetime
        
        if tenant_id not in self.tenant_tokens:
            self.tenant_tokens[tenant_id] = {}
        
        self.tenant_tokens[tenant_id]['token'] = token_data
        if refresh_token:
            self.tenant_tokens[tenant_id]['refresh_token'] = refresh_token
        if expires_at:
            self.tenant_tokens[tenant_id]['expires_at'] = expires_at.isoformat() if hasattr(expires_at, 'isoformat') else expires_at
        if connected_at:
            self.tenant_tokens[tenant_id]['connected_at'] = connected_at.isoformat() if hasattr(connected_at, 'isoformat') else connected_at
        elif 'connected_at' not in self.tenant_tokens[tenant_id]:
            self.tenant_tokens[tenant_id]['connected_at'] = timezone.now().isoformat()
        
        self.save(update_fields=['tenant_tokens'])
    
    def get_all_tenant_ids(self):
        """Get list of all tenant IDs that have tokens."""
        return list(self.tenant_tokens.keys())


class XeroTenantToken(models.Model):
    tenant = models.ForeignKey(XeroTenant, on_delete=models.CASCADE, related_name='tenant_tokens')
    credentials = models.ForeignKey('XeroClientCredentials', on_delete=models.CASCADE, related_name='xero_tenant_tokens')
    token = models.JSONField()  # Tenant-specific token
    refresh_token = models.CharField(max_length=1000)
    expires_at = models.DateTimeField()
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('tenant', 'credentials')]

    def __str__(self):
        return f"Token for {self.tenant.tenant_name}"


class XeroAuthSettings(models.Model):
    access_token_url = models.CharField(max_length=255)
    refresh_url = models.CharField(max_length=255)
    auth_url = models.CharField(max_length=255)
