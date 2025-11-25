from django.contrib import admin
from apps.xero.xero_core.models import XeroTenant


@admin.register(XeroTenant)
class XeroTenantAdmin(admin.ModelAdmin):
    list_display = ('tenant_id', 'tenant_name')
    search_fields = ('tenant_id', 'tenant_name')
    readonly_fields = ('tenant_id',)
