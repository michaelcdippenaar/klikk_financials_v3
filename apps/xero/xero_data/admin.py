from django.contrib import admin
from apps.xero.xero_data.models import XeroTransactionSource, XeroJournalsSource, XeroJournals


@admin.register(XeroTransactionSource)
class XeroTransactionSourceAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'transactions_id', 'transaction_source', 'contact')
    list_filter = ('organisation', 'transaction_source')
    search_fields = ('transactions_id', 'organisation__tenant_name', 'contact__name')
    readonly_fields = ('transactions_id',)


@admin.register(XeroJournalsSource)
class XeroJournalsSourceAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'journal_id', 'journal_number', 'journal_type', 'processed')
    list_filter = ('organisation', 'journal_type', 'processed')
    search_fields = ('journal_id', 'organisation__tenant_name')
    readonly_fields = ('journal_id',)


@admin.register(XeroJournals)
class XeroJournalsAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'journal_id', 'journal_number', 'journal_type', 'date', 'account', 'amount')
    list_filter = ('organisation', 'journal_type', 'date', 'account__type')
    search_fields = ('journal_id', 'description', 'reference', 'organisation__tenant_name', 'account__name')
    readonly_fields = ('journal_id',)
    date_hierarchy = 'date'
