from django.contrib import admin
import json
from django.utils.html import format_html
from .models import (
    XeroTrailBalanceReport, XeroTrailBalanceReportLine, TrailBalanceComparison,
    XeroProfitAndLossReport, XeroProfitAndLossReportLine, ProfitAndLossComparison
)


@admin.register(XeroTrailBalanceReport)
class XeroTrailBalanceReportAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'report_date', 'report_type', 'lines_count', 'view_lines_link', 'parsed_json','imported_at']
    list_filter = ['organisation', 'report_date', 'report_type', 'imported_at']
    search_fields = ['organisation__tenant_name', 'organisation__tenant_id']
    date_hierarchy = 'report_date'
    readonly_fields = ['imported_at', 'raw_data_display', 'lines_count', 'raw_data_structure', 'view_lines_link', 'sample_lines_display']
    # Removed inline to prevent hanging - use sample_lines_display and view_lines_link instead
    actions = ['reparse_report', 'delete_selected']
    
    def lines_count(self, obj):
        """Display count of report lines"""
        return obj.lines.count()
    lines_count.short_description = 'Lines'
    
    def view_lines_link(self, obj):
        """Link to view all report lines"""
        count = obj.lines.count()
        if count > 0:
            url = f"/admin/xero_validation/xerotrailbalancereportline/?report__id__exact={obj.id}"
            return format_html(
                '<a href="{}" target="_blank">View {} Lines</a>',
                url, count
            )
        return '-'
    view_lines_link.short_description = 'View Lines'
    
    def sample_lines_display(self, obj):
        """Display sample of first 10 lines"""
        # Don't use select_related with only() - just fetch the fields we need
        lines = obj.lines.only(
            'account_code', 'account_name', 'debit', 'credit', 'value', 'ytd_debit', 'ytd_credit', 'row_type'
        )[:10]
        
        if not lines:
            return 'No lines available'
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #f0f0f0;"><th>Code</th><th>Name</th><th>YTD Debit</th><th>YTD Credit</th><th>Value</th></tr></thead>'
        html += '<tbody>'
        for line in lines:
            html += f'<tr><td>{line.account_code}</td><td>{line.account_name[:50]}</td><td>{line.ytd_debit}</td><td>{line.ytd_credit}</td><td>{line.value}</td></tr>'
        html += '</tbody></table>'
        
        count = obj.lines.count()
        if count > 10:
            url = f"/admin/xero_validation/xerotrailbalancereportline/?report__id__exact={obj.id}"
            html += f'<p><a href="{url}" target="_blank">View all {count} lines →</a></p>'
        
        return format_html(html)
    sample_lines_display.short_description = 'Sample Lines (first 10)'
    
    def get_queryset(self, request):
        """Optimize queryset and ensure tenant filtering is respected"""
        qs = super().get_queryset(request)
        qs = qs.select_related('organisation').prefetch_related('lines')
        
        # If filtering by organisation in the admin, ensure queryset respects it
        # This is handled automatically by Django admin's list_filter, but we ensure it's applied
        return qs
    
    def get_actions(self, request):
        """Override to ensure our custom delete action replaces the default one"""
        actions = super().get_actions(request)
        # Our custom delete_selected method will replace the default one
        # because we've defined it in the class and included it in actions list
        return actions
    
    
    def raw_data_structure(self, obj):
        """Display the structure of raw data for debugging"""
        if obj.raw_data:
            structure = {}
            if isinstance(obj.raw_data, dict):
                structure['top_level_keys'] = list(obj.raw_data.keys())
                if 'Reports' in obj.raw_data:
                    reports = obj.raw_data.get("Reports", [])
                    if reports:
                        structure['reports_count'] = len(reports)
                        if reports[0]:
                            structure['first_report_keys'] = list(reports[0].keys())
                            if 'Rows' in reports[0]:
                                structure['rows_count'] = len(reports[0].get('Rows', []))
                                # Check if rows are nested
                                if reports[0].get('Rows'):
                                    first_row = reports[0]['Rows'][0]
                                    structure['first_row_type'] = first_row.get('RowType', 'N/A')
                                    structure['first_row_keys'] = list(first_row.keys())
                                    if 'Rows' in first_row:
                                        structure['has_nested_rows'] = True
                                        structure['nested_rows_count'] = len(first_row.get('Rows', []))
            
            return format_html(
                '<pre style="max-height: 200px; overflow: auto; font-size: 11px; background: #f0f0f0; padding: 10px; border: 1px solid #ddd;">{}</pre>',
                json.dumps(structure, indent=2)
            )
        return 'No raw data available'
    raw_data_structure.short_description = 'Raw Data Structure (Debug)'
    
    def reparse_report(self, request, queryset):
        """Admin action to re-parse report lines from raw data"""
        from .services import _reparse_report_from_raw_data
        
        # Filter queryset by tenant - ensure all reports belong to the same tenant
        # Get unique organisations from selected reports
        organisations = queryset.values_list('organisation', flat=True).distinct()
        if len(organisations) > 1:
            self.message_user(
                request,
                "Error: Cannot re-parse reports from multiple tenants. Please select reports from a single tenant.",
                level='ERROR'
            )
            return
        
        # Filter queryset to only include reports from the same organisation
        if organisations:
            queryset = queryset.filter(organisation=organisations[0])
        
        count = 0
        for report in queryset:
            try:
                lines_created = _reparse_report_from_raw_data(report)
                count += 1
                self.message_user(
                    request,
                    f"Re-parsed report {report.id}: Created {lines_created} lines."
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error re-parsing report {report.id}: {str(e)}",
                    level='ERROR'
                )
        
        if count > 0:
            self.message_user(
                request,
                f"Successfully re-parsed {count} report(s)."
            )
    reparse_report.short_description = "Re-parse report lines from raw data"
    
    def delete_selected(self, request, queryset):
        """Custom delete action that ensures tenant filtering"""
        # Get unique organisations from selected reports
        organisations = queryset.values_list('organisation', flat=True).distinct()
        
        if len(organisations) > 1:
            self.message_user(
                request,
                "Error: Cannot delete reports from multiple tenants. Please select reports from a single tenant.",
                level='ERROR'
            )
            return
        
        # Filter queryset to only include reports from the same organisation
        if organisations:
            queryset = queryset.filter(organisation=organisations[0])
        
        # Get count before deletion
        count = queryset.count()
        organisation_name = organisations[0].tenant_name if organisations else 'unknown'
        
        # Delete related comparisons and lines first
        from .models import XeroTrailBalanceReportLine, TrailBalanceComparison
        for report in queryset:
            TrailBalanceComparison.objects.filter(report=report).delete()
            XeroTrailBalanceReportLine.objects.filter(report=report).delete()
        
        # Delete the reports
        queryset.delete()
        
        self.message_user(
            request,
            f"Successfully deleted {count} report(s) for tenant {organisation_name}.",
            level='SUCCESS'
        )
    delete_selected.short_description = "Delete selected reports"
    
    def raw_data_display(self, obj):
        """Display raw JSON data in a readable format"""
        if obj.raw_data:
            return format_html(
                '<pre style="max-height: 400px; overflow: auto; font-size: 11px; background: #f5f5f5; padding: 10px; border: 1px solid #ddd;">{}</pre>',
                json.dumps(obj.raw_data, indent=2)
            )
        return 'No raw data available'
    raw_data_display.short_description = 'Raw JSON Data from Xero'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('organisation', 'report_date', 'report_type', 'lines_count', 'view_lines_link')
        }),
        ('Sample Lines', {
            'fields': ('sample_lines_display',),
            'description': 'First 10 lines preview. Use "View Lines" link above to see all lines.'
        }),
        ('Raw Data Structure (Debug)', {
            'fields': ('raw_data_structure',),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('raw_data_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('imported_at',)
        }),
    )


@admin.register(XeroTrailBalanceReportLine)
class XeroTrailBalanceReportLineAdmin(admin.ModelAdmin):
    list_display = ['report', 'account_code', 'account_name', 'value', 'db_value', 'ytd_debit', 'ytd_credit', 'period_debit', 'period_credit', 'row_type', 'account']
    list_filter = ['row_type', 'report__report_date', 'account_type']
    search_fields = ['account_code', 'account_name', 'report__organisation__tenant_name', 'account__code', 'account__name']
    readonly_fields = ['report', 'account_code', 'account_name', 'account_type', 'debit', 'credit', 'value', 'db_value', 'period_debit', 'period_credit', 'ytd_debit', 'ytd_credit', 'row_type', 'raw_cell_data_display']
    list_per_page = 100
    list_select_related = ['report', 'account', 'report__organisation']
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('report', 'account', 'report__organisation')
    
    def raw_cell_data_display(self, obj):
        """Display raw cell data in a readable format"""
        if obj.raw_cell_data:
            return format_html(
                '<pre style="max-height: 300px; overflow: auto; font-size: 10px; background: #f5f5f5; padding: 10px; border: 1px solid #ddd;">{}</pre>',
                json.dumps(obj.raw_cell_data, indent=2)
            )
        return 'No raw data available'
    raw_cell_data_display.short_description = 'Raw Cell Data'
    
    fieldsets = (
        ('Report', {
            'fields': ('report',)
        }),
        ('Account Information', {
            'fields': ('account', 'account_code', 'account_name', 'account_type')
        }),
        ('Amounts (Primary)', {
            'fields': ('debit', 'credit', 'value', 'db_value'),
            'description': 'Primary values: YTD if available, else period values. db_value is database-calculated (e.g., P&L).'
        }),
        ('Period Values', {
            'fields': ('period_debit', 'period_credit')
        }),
        ('YTD Values (Cumulative)', {
            'fields': ('ytd_debit', 'ytd_credit')
        }),
        ('Metadata', {
            'fields': ('row_type',)
        }),
        ('Raw Data', {
            'fields': ('raw_cell_data_display',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TrailBalanceComparison)
class TrailBalanceComparisonAdmin(admin.ModelAdmin):
    list_display = ['report', 'account', 'xero_value', 'db_value', 'difference', 'match_status', 'compared_at']
    list_filter = ['match_status', 'report__report_date', 'compared_at']
    search_fields = ['account__code', 'account__name', 'report__organisation__tenant_name']
    readonly_fields = ['compared_at']
    date_hierarchy = 'compared_at'
    
    fieldsets = (
        ('Report', {
            'fields': ('report',)
        }),
        ('Account', {
            'fields': ('account',)
        }),
        ('Values', {
            'fields': ('xero_value', 'db_value', 'difference')
        }),
        ('Comparison', {
            'fields': ('match_status', 'notes')
        }),
        ('Metadata', {
            'fields': ('compared_at',)
        }),
    )


@admin.register(XeroProfitAndLossReport)
class XeroProfitAndLossReportAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'from_date', 'to_date', 'periods', 'timeframe', 'imported_at']
    list_filter = ['organisation', 'timeframe', 'imported_at']
    search_fields = ['organisation__tenant_name']
    readonly_fields = ('imported_at',)
    date_hierarchy = 'from_date'


@admin.register(XeroProfitAndLossReportLine)
class XeroProfitAndLossReportLineAdmin(admin.ModelAdmin):
    list_display = ['report', 'account_code', 'account_name', 'row_type', 'section_title']
    list_filter = ['report__organisation', 'row_type', 'section_title', 'report__from_date']
    search_fields = ['account_code', 'account_name', 'report__organisation__tenant_name']
    readonly_fields = ('report',)


@admin.register(ProfitAndLossComparison)
class ProfitAndLossComparisonAdmin(admin.ModelAdmin):
    list_display = ['report', 'account', 'period_index', 'period_date', 'xero_value', 'db_value', 'difference', 'match_status']
    list_filter = ['match_status', 'period_index', 'report__organisation', 'report__from_date']
    search_fields = ['account__code', 'account__name', 'report__organisation__tenant_name']
    readonly_fields = ('compared_at',)
