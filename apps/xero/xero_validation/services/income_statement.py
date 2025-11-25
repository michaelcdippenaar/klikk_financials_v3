"""
Income statement services for trail balance reports.
"""
import logging
from decimal import Decimal

from django.db.models import Sum

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_metadata.models import XeroAccount
from apps.xero.xero_cube.models import XeroTrailBalance
from ..models import XeroTrailBalanceReport, XeroTrailBalanceReportLine

logger = logging.getLogger(__name__)


def add_income_statement_to_trail_balance_report(report_id=None, tenant_id=None, target_account_code='960'):
    """
    Add income statement (P&L) entries to a trial balance report.
    Calculates cumulative P&L for each financial year end from XeroTrailBalance.
    Uses the latest report if report_id is not provided.
    
    Args:
        report_id: ID of XeroTrailBalanceReport (optional)
        tenant_id: Xero tenant ID (optional, used if report_id not provided)
        target_account_code: Account code to use for P&L entry (default '960')
    
    Returns:
        dict: Result with lines created and P&L values
    """
    if report_id:
        report = XeroTrailBalanceReport.objects.get(id=report_id)
    elif tenant_id:
        organisation = XeroTenant.objects.get(tenant_id=tenant_id)
        report = XeroTrailBalanceReport.objects.filter(
            organisation=organisation
        ).order_by('-report_date', '-imported_at').first()
    else:
        raise ValueError("Either report_id or tenant_id must be provided")
    
    if not report:
        raise ValueError("No trail balance report found")
    
    organisation = report.organisation
    report_date = report.report_date
    report_year = report_date.year
    
    # Get target account
    try:
        target_account = XeroAccount.objects.get(
            organisation=organisation,
            code=target_account_code
        )
    except XeroAccount.DoesNotExist:
        raise ValueError(f"Target account with code {target_account_code} not found")
    
    # Get income statement accounts (Revenue and Expense)
    income_statement_types = ['REVENUE', 'EXPENSE']
    
    # Calculate cumulative P&L up to report date
    # Get all periods up to and including report month
    report_month = report_date.month
    
    # Get revenue and expense totals
    revenue_total = XeroTrailBalance.objects.filter(
        organisation=organisation,
        account__type='REVENUE',
        year=report_year,
        month__lte=report_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    expense_total = XeroTrailBalance.objects.filter(
        organisation=organisation,
        account__type='EXPENSE',
        year=report_year,
        month__lte=report_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate P&L (Revenue - Expenses)
    pnl_value = revenue_total - expense_total
    
    # Check if line already exists
    existing_line = XeroTrailBalanceReportLine.objects.filter(
        report=report,
        account=target_account
    ).first()
    
    if existing_line:
        # Update existing line
        existing_line.value = pnl_value
        existing_line.debit = pnl_value if pnl_value > 0 else Decimal('0')
        existing_line.credit = -pnl_value if pnl_value < 0 else Decimal('0')
        existing_line.save()
        lines_created = 0
    else:
        # Create new line
        XeroTrailBalanceReportLine.objects.create(
            report=report,
            account=target_account,
            account_code=target_account_code,
            account_name=f"Income Statement (P&L) - {report_date}",
            account_type=target_account.type,
            debit=pnl_value if pnl_value > 0 else Decimal('0'),
            credit=-pnl_value if pnl_value < 0 else Decimal('0'),
            value=pnl_value,
            row_type='Row'
        )
        lines_created = 1
    
    return {
        'success': True,
        'message': f"Income statement entry added to report {report.id}",
        'lines_created': lines_created,
        'pnl_value': pnl_value,
        'revenue_total': revenue_total,
        'expense_total': expense_total,
        'report_id': report.id,
        'report_date': report_date
    }

