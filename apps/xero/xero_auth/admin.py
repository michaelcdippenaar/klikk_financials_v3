from django.contrib import admin
from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken, XeroAuthSettings


@admin.register(XeroClientCredentials)
class XeroClientCredentialsAdmin(admin.ModelAdmin):
    list_display = ('user', 'client_id', 'active', 'expires_at')
    list_filter = ('active',)
    search_fields = ('user__username', 'user__email', 'client_id')
    # Removed readonly_fields to allow user selection when creating/editing


@admin.register(XeroTenantToken)
class XeroTenantTokenAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'credentials', 'expires_at', 'connected_at')
    list_filter = ('connected_at', 'expires_at')
    search_fields = ('tenant__tenant_name', 'tenant__tenant_id', 'credentials__user__username')
    readonly_fields = ('connected_at',)


@admin.register(XeroAuthSettings)
class XeroAuthSettingsAdmin(admin.ModelAdmin):
    list_display = ('access_token_url', 'refresh_url', 'auth_url')
