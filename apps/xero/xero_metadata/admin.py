from django.contrib import admin
from apps.xero.xero_metadata.models import XeroBusinessUnits, XeroAccount, XeroTracking, XeroContacts


@admin.register(XeroBusinessUnits)
class XeroBusinessUnitsAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'business_unit_code', 'division_code', 'business_unit_description', 'division_description')
    list_filter = ('organisation', 'business_unit_code', 'division_code')
    search_fields = ('organisation__tenant_name', 'business_unit_description', 'division_description')


@admin.register(XeroAccount)
class XeroAccountAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'code', 'name', 'type', 'grouping', 'business_unit')
    list_filter = ('organisation', 'type', 'grouping', 'business_unit')
    search_fields = ('code', 'name', 'account_id', 'organisation__tenant_name')
    readonly_fields = ('account_id',)


@admin.register(XeroTracking)
class XeroTrackingAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'name', 'option')
    list_filter = ('organisation', 'name')
    search_fields = ('name', 'option', 'organisation__tenant_name')


@admin.register(XeroContacts)
class XeroContactsAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'contacts_id', 'name')
    list_filter = ('organisation',)
    search_fields = ('name', 'contacts_id', 'organisation__tenant_name')
    readonly_fields = ('contacts_id',)
