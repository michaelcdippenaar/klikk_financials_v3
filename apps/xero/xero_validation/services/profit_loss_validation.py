"""
Profit & Loss validation service - checks if P&L data is out of sync.
Validates by comparing balances and checking for missing accounts.
"""
import logging
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_cube.models import XeroTrailBalance
from apps.xero.xero_validation.models import XeroProfitAndLossReport, XeroProfitAndLossReportLine
from apps.xero.xero_sync.models import XeroLastUpdate

logger = logging.getLogger(__name__)


def validate_profit_loss_sync(tenant_id, report_id=None, tolerance=Decimal('0.01')):
    """
    Validate if P&L report is in sync with Trail Balance data.
    
    Checks:
    1. If balances differ between P&L report and Trail Balance
    2. If accounts exist in P&L but not in Trail Balance (or vice versa)
    
    Args:
        tenant_id: Xero tenant ID
        report_id: Optional P&L report ID. If not provided, uses most recent report.
        tolerance: Tolerance for balance differences (default 0.01)
    
    Returns:
        dict: {
            'in_sync': bool,
            'errors': list of error messages,
            'balance_differences': list of accounts with balance differences,
            'missing_accounts': list of missing accounts
        }
    """
    try:
        organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    except XeroTenant.DoesNotExist:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    # Get P&L report
    if report_id:
        try:
            pnl_report = XeroProfitAndLossReport.objects.get(
                id=report_id,
                organisation=organisation
            )
        except XeroProfitAndLossReport.DoesNotExist:
            raise ValueError(f"P&L report {report_id} not found")
    else:
        # Get most recent P&L report
        pnl_report = XeroProfitAndLossReport.objects.filter(
            organisation=organisation
        ).order_by('-to_date', '-created_at').first()
        
        if not pnl_report:
            return {
                'in_sync': False,
                'errors': ['No P&L report found for validation'],
                'balance_differences': [],
                'missing_accounts': []
            }
    
    errors = []
    balance_differences = []
    missing_accounts = []
    
    # Get P&L report lines
    pnl_lines = XeroProfitAndLossReportLine.objects.filter(
        report=pnl_report
    ).select_related('account')
    
    # Get Trail Balance data for P&L account types (REVENUE, EXPENSE)
    # Filter by the report date range
    tb_records = XeroTrailBalance.objects.filter(
        organisation=organisation,
        account__type__in=['REVENUE', 'EXPENSE'],
        year__gte=pnl_report.from_date.year,
        year__lte=pnl_report.to_date.year,
    ).select_related('account')
    
    # Create a map of account codes to Trail Balance totals
    tb_account_totals = {}
    for tb_record in tb_records:
        account_code = tb_record.account.code if tb_record.account else None
        if account_code:
            if account_code not in tb_account_totals:
                tb_account_totals[account_code] = Decimal('0')
            # Sum amounts for this account across all periods in the report range
            tb_account_totals[account_code] += tb_record.amount
    
    # Check each P&L line
    pnl_account_codes = set()
    for line in pnl_lines:
        account_code = line.account_code
        pnl_account_codes.add(account_code)
        
        # Get total from P&L report (sum of all period values)
        pnl_total = Decimal('0')
        if line.period_values:
            for period_value in line.period_values.values():
                try:
                    pnl_total += Decimal(str(period_value))
                except (ValueError, TypeError):
                    pass
        
        # Get Trail Balance total
        tb_total = tb_account_totals.get(account_code, Decimal('0'))
        
        # Check for balance difference
        difference = abs(pnl_total - tb_total)
        if difference > tolerance:
            balance_differences.append({
                'account_code': account_code,
                'account_name': line.account_name,
                'pnl_total': float(pnl_total),
                'tb_total': float(tb_total),
                'difference': float(difference)
            })
            errors.append(
                f"Account {account_code} ({line.account_name}): "
                f"P&L total {pnl_total} differs from Trail Balance total {tb_total} "
                f"(difference: {difference})"
            )
        
        # Check if account exists in Trail Balance
        if account_code not in tb_account_totals:
            missing_accounts.append({
                'account_code': account_code,
                'account_name': line.account_name,
                'pnl_total': float(pnl_total)
            })
            errors.append(
                f"Account {account_code} ({line.account_name}) exists in P&L "
                f"but not found in Trail Balance"
            )
    
    # Check for accounts in Trail Balance but not in P&L
    tb_account_codes = set(tb_account_totals.keys())
    missing_in_pnl = tb_account_codes - pnl_account_codes
    for account_code in missing_in_pnl:
        tb_total = tb_account_totals[account_code]
        if abs(tb_total) > tolerance:  # Only report if balance is significant
            missing_accounts.append({
                'account_code': account_code,
                'account_name': f"Account {account_code}",
                'tb_total': float(tb_total),
                'missing_in': 'pnl'
            })
            errors.append(
                f"Account {account_code} exists in Trail Balance "
                f"(total: {tb_total}) but not found in P&L report"
            )
    
    in_sync = len(errors) == 0
    
    result = {
        'in_sync': in_sync,
        'errors': errors,
        'balance_differences': balance_differences,
        'missing_accounts': missing_accounts,
        'report_id': pnl_report.id,
        'report_from_date': pnl_report.from_date.isoformat(),
        'report_to_date': pnl_report.to_date.isoformat(),
    }
    
    logger.info(
        f"P&L validation for tenant {tenant_id}: "
        f"{'IN SYNC' if in_sync else 'OUT OF SYNC'} "
        f"({len(balance_differences)} balance differences, "
        f"{len(missing_accounts)} missing accounts)"
    )
    
    return result


def validate_profit_loss_with_fallback(tenant_id, tolerance=Decimal('0.01')):
    """
    Validate P&L and if it fails, try validating against previous month.
    If still not valid, mark as out of sync.
    
    Args:
        tenant_id: Xero tenant ID
        tolerance: Tolerance for balance differences
    
    Returns:
        dict: Validation result with fallback attempt
    """
    organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    
    # Try current month validation
    result = validate_profit_loss_sync(tenant_id, tolerance=tolerance)
    
    if result['in_sync']:
        # Validation passed - timestamp already updated after API call
        return result
    
    # Try previous month
    logger.info(f"P&L validation failed for tenant {tenant_id}, trying previous month...")
    
    # Get previous month's report
    today = date.today()
    prev_month_end = today.replace(day=1) - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    
    prev_report = XeroProfitAndLossReport.objects.filter(
        organisation=organisation,
        from_date__lte=prev_month_start,
        to_date__gte=prev_month_end
    ).order_by('-to_date').first()
    
    if prev_report:
        prev_result = validate_profit_loss_sync(tenant_id, report_id=prev_report.id, tolerance=tolerance)
        
        if prev_result['in_sync']:
            # Previous month is valid, but current is not - don't update timestamp
            error_msg = (
                f"Current P&L validation failed but previous month ({prev_month_start} to {prev_month_end}) "
                f"is valid. Errors: {', '.join(result['errors'][:3])}"
            )
            # Don't update timestamp - preserve last successful date
            logger.warning(f"P&L validation failed for tenant {tenant_id}: {error_msg}")
            return {
                **result,
                'fallback_attempted': True,
                'fallback_valid': True,
                'out_of_sync': True
            }
        else:
            # Both failed - don't update timestamp
            error_msg = (
                f"P&L validation failed for both current and previous month. "
                f"Current errors: {', '.join(result['errors'][:3])}"
            )
            # Don't update timestamp - preserve last successful date
            logger.error(f"P&L validation failed for tenant {tenant_id}: {error_msg}")
            return {
                **result,
                'fallback_attempted': True,
                'fallback_valid': False,
                'out_of_sync': True
            }
    else:
        # No previous month report found - don't update timestamp
        error_msg = (
            f"P&L validation failed and no previous month report found. "
            f"Errors: {', '.join(result['errors'][:3])}"
        )
        # Don't update timestamp - preserve last successful date
        logger.error(f"P&L validation failed for tenant {tenant_id}: {error_msg}")
        
        logger.error(f"P&L marked as out of sync for tenant {tenant_id}: {error_msg}")
        return {
            **result,
            'fallback_attempted': False,
            'fallback_valid': False,
            'out_of_sync': True
        }

