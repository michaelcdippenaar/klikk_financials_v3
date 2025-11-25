from django.db import models
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_metadata.models import XeroAccount


class XeroTrailBalanceReport(models.Model):
    """
    Stores imported trail balance reports from Xero API.
    """
    organisation = models.ForeignKey(XeroTenant, on_delete=models.CASCADE, related_name='xero_trail_balance_reports')
    report_date = models.DateField(help_text="Date of the report")
    report_type = models.CharField(max_length=50, default='TrialBalance', help_text="Type of report from Xero")
    imported_at = models.DateTimeField(auto_now_add=True, help_text="When this report was imported")
    raw_data = models.JSONField(null=True, blank=True, help_text="Raw JSON data from Xero API")
    parsed_json = models.JSONField(null=True, blank=True, help_text="Parsed JSON data from trial balance parser")
    
    class Meta:
        ordering = ['-report_date', '-imported_at']
        indexes = [
            models.Index(fields=['organisation', 'report_date'], name='xero_tb_rpt_org_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.organisation.tenant_name}: Trail Balance Report {self.report_date}"


class XeroTrailBalanceReportLine(models.Model):
    """
    Individual line items from Xero trail balance report.
    """
    report = models.ForeignKey(XeroTrailBalanceReport, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(XeroAccount, on_delete=models.CASCADE, related_name='xero_report_lines', null=True, blank=True)
    account_code = models.CharField(max_length=50, help_text="Account code from Xero")
    account_name = models.CharField(max_length=255, help_text="Account name from Xero")
    account_type = models.CharField(max_length=50, null=True, blank=True, help_text="Account type from Xero")
    # Primary fields (YTD if available, else period)
    debit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Debit amount (YTD if available, else period)")
    credit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Credit amount (YTD if available, else period)")
    value = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Net value (debit - credit)")
    # Period values (for this period only)
    period_debit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Period debit amount")
    period_credit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="Period credit amount")
    # YTD values (cumulative year-to-date)
    ytd_debit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="YTD debit amount (cumulative)")
    ytd_credit = models.DecimalField(max_digits=30, decimal_places=2, default=0, help_text="YTD credit amount (cumulative)")
    # Database calculated value (for P&L and other calculated entries)
    db_value = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True, help_text="Value calculated from database (e.g., P&L from XeroTrailBalance)")
    row_type = models.CharField(max_length=50, null=True, blank=True, help_text="Row type (e.g., Header, Row, SummaryRow)")
    raw_cell_data = models.JSONField(null=True, blank=True, help_text="Raw cell data from Xero API")
    
    class Meta:
        ordering = ['account_code']
        indexes = [
            models.Index(fields=['report', 'account_code'], name='xero_tb_rpt_line_code_idx'),
            models.Index(fields=['report', 'account'], name='xero_tb_rpt_line_acc_idx'),
        ]
    
    def __str__(self):
        return f"{self.report.organisation.tenant_name}: {self.account_code} - {self.account_name} ({self.value})"


class TrailBalanceComparison(models.Model):
    """
    Stores comparison results between Xero trail balance report and our database.
    """
    report = models.ForeignKey(XeroTrailBalanceReport, on_delete=models.CASCADE, related_name='comparisons')
    account = models.ForeignKey(XeroAccount, on_delete=models.CASCADE, related_name='trail_balance_comparisons')
    xero_value = models.DecimalField(max_digits=30, decimal_places=2, help_text="Value from Xero report")
    db_value = models.DecimalField(max_digits=30, decimal_places=2, help_text="Value from our database")
    difference = models.DecimalField(max_digits=30, decimal_places=2, help_text="Difference (xero_value - db_value)")
    match_status = models.CharField(
        max_length=20,
        choices=[
            ('match', 'Match'),
            ('mismatch', 'Mismatch'),
            ('missing_in_db', 'Missing in DB'),
            ('missing_in_xero', 'Missing in Xero'),
        ],
        help_text="Status of the comparison"
    )
    notes = models.TextField(blank=True, help_text="Additional notes about the comparison")
    compared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-difference', 'account__code']
        indexes = [
            models.Index(fields=['report', 'match_status'], name='xero_tb_comp_status_idx'),
            models.Index(fields=['report', 'account'], name='xero_tb_comp_acc_idx'),
        ]
    
    def __str__(self):
        return f"{self.report.organisation.tenant_name}: {self.account.code} - {self.match_status} (Diff: {self.difference})"


class XeroProfitAndLossReport(models.Model):
    """
    Stores imported Profit and Loss reports from Xero API.
    """
    organisation = models.ForeignKey(XeroTenant, on_delete=models.CASCADE, related_name='xero_pnl_reports')
    from_date = models.DateField(help_text="Start date of the report period")
    to_date = models.DateField(help_text="End date of the report period")
    periods = models.IntegerField(default=12, help_text="Number of periods in the report")
    timeframe = models.CharField(max_length=20, default='MONTH', help_text="Timeframe (MONTH, QUARTER, YEAR)")
    imported_at = models.DateTimeField(auto_now_add=True, help_text="When this report was imported")
    raw_data = models.JSONField(null=True, blank=True, help_text="Raw JSON data from Xero API")
    
    class Meta:
        ordering = ['-to_date', '-imported_at']
        indexes = [
            models.Index(fields=['organisation', 'from_date', 'to_date'], name='xero_pnl_rpt_org_dates_idx'),
        ]
    
    def __str__(self):
        return f"{self.organisation.tenant_name}: P&L Report {self.from_date} to {self.to_date}"


class XeroProfitAndLossReportLine(models.Model):
    """
    Individual line items from Xero Profit and Loss report.
    Stores values for each period (month) in the report.
    """
    report = models.ForeignKey(XeroProfitAndLossReport, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(XeroAccount, on_delete=models.CASCADE, related_name='xero_pnl_report_lines', null=True, blank=True)
    account_code = models.CharField(max_length=50, blank=True, help_text="Account code from Xero")
    account_name = models.CharField(max_length=255, help_text="Account name or section title")
    account_type = models.CharField(max_length=50, null=True, blank=True, help_text="Account type from Xero")
    row_type = models.CharField(max_length=50, help_text="Row type (Header, Section, Row, SummaryRow)")
    section_title = models.CharField(max_length=255, blank=True, help_text="Section title (e.g., 'Income', 'Expenses')")
    
    # Period values - store as JSON for flexibility (12 months)
    period_values = models.JSONField(default=dict, help_text="Dictionary of period values: {'period_0': value, 'period_1': value, ...}")
    
    raw_cell_data = models.JSONField(null=True, blank=True, help_text="Raw cell data from Xero API")
    
    class Meta:
        ordering = ['report', 'account_code', 'id']
        indexes = [
            models.Index(fields=['report', 'account_code'], name='xero_pnl_rpt_line_code_idx'),
            models.Index(fields=['report', 'account'], name='xero_pnl_rpt_line_acc_idx'),
            models.Index(fields=['report', 'row_type'], name='xero_pnl_rpt_line_type_idx'),
        ]
    
    def __str__(self):
        return f"{self.report.organisation.tenant_name}: {self.account_code or self.account_name} - {self.row_type}"


class ProfitAndLossComparison(models.Model):
    """
    Stores comparison results between Xero P&L report and our database trail balance.
    Compares per month for each account.
    """
    report = models.ForeignKey(XeroProfitAndLossReport, on_delete=models.CASCADE, related_name='comparisons')
    account = models.ForeignKey(XeroAccount, on_delete=models.CASCADE, related_name='pnl_comparisons')
    period_index = models.IntegerField(help_text="Period index (0-11 for 12 months)")
    period_date = models.DateField(help_text="Date representing this period (first day of month)")
    xero_value = models.DecimalField(max_digits=30, decimal_places=2, help_text="Value from Xero P&L report")
    db_value = models.DecimalField(max_digits=30, decimal_places=2, help_text="Value from our database (XeroTrailBalance)")
    difference = models.DecimalField(max_digits=30, decimal_places=2, help_text="Difference (xero_value - db_value)")
    match_status = models.CharField(
        max_length=20,
        choices=[
            ('match', 'Match'),
            ('mismatch', 'Mismatch'),
            ('missing_in_db', 'Missing in DB'),
            ('missing_in_xero', 'Missing in Xero'),
        ],
        help_text="Status of the comparison"
    )
    notes = models.TextField(blank=True, help_text="Additional notes about the comparison")
    compared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['report', 'period_index', 'account__code']
        indexes = [
            models.Index(fields=['report', 'period_index', 'match_status'], name='xero_pnl_comp_prd_st_idx'),
            models.Index(fields=['report', 'account', 'period_index'], name='xero_pnl_comp_acc_prd_idx'),
        ]
        unique_together = [('report', 'account', 'period_index')]
    
    def __str__(self):
        return f"{self.report.organisation.tenant_name}: {self.account.code} - Period {self.period_index} - {self.match_status} (Diff: {self.difference})"
