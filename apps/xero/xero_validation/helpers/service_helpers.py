"""
Service helper utilities for validation services.

These helpers are used by service layer functions.
"""
import logging
from decimal import Decimal

from apps.xero.xero_metadata.models import XeroAccount
from ..models import XeroTrailBalanceReport, XeroTrailBalanceReportLine
from .trial_balance_parser import parse_trial_balance_dict

logger = logging.getLogger(__name__)


def convert_decimals_to_strings(obj):
    """
    Recursively convert Decimal objects to strings for JSON serialization.
    
    Args:
        obj: Object that may contain Decimal values (dict, list, Decimal, etc.)
    
    Returns:
        Object with all Decimal values converted to strings
    """
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_strings(item) for item in obj]
    else:
        return obj


def reparse_report_from_raw_data(report_id):
    """
    Re-parse a report from its raw_data field.
    Useful if parsing logic has changed.
    
    Args:
        report_id: ID of XeroTrailBalanceReport
    
    Returns:
        dict: Result with lines created
    """
    report = XeroTrailBalanceReport.objects.get(id=report_id)
    
    # Delete existing lines
    report.lines.all().delete()
    
    # Re-parse
    parsed_rows = parse_trial_balance_dict(report.raw_data)
    lines_created = 0
    
    for row in parsed_rows:
        account = None
        
        if row["account_id_uuid"]:
            try:
                account = XeroAccount.objects.get(
                    organisation=report.organisation,
                    account_id=row["account_id_uuid"],
                )
            except XeroAccount.DoesNotExist:
                account = None
        
        if not account and row["account_code"]:
            try:
                account = XeroAccount.objects.get(
                    organisation=report.organisation,
                    code=row["account_code"],
                )
            except XeroAccount.DoesNotExist:
                account = (
                    XeroAccount.objects.filter(
                        organisation=report.organisation,
                        code__iexact=row["account_code"].strip(),
                    ).first()
                    or None
                )
        
        XeroTrailBalanceReportLine.objects.create(
            report=report,
            account=account,
            account_code=row["account_code"],
            account_name=row["account_name"],
            account_type=None,
            debit=row["debit"],
            credit=row["credit"],
            value=row["value"],
            row_type=row["row_type"],
            raw_cell_data={"row": row["raw_row"]},
        )
        lines_created += 1
    
    return {
        'success': True,
        'message': f"Re-parsed report {report_id}, created {lines_created} lines",
        'lines_created': lines_created
    }

