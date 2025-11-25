"""
Parser for Xero Profit and Loss reports.
Handles multi-period P&L reports with monthly columns.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from django.utils import timezone

from django.utils import timezone
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_metadata.models import XeroAccount
from ..models import XeroProfitAndLossReport, XeroProfitAndLossReportLine

logger = logging.getLogger(__name__)


def parse_profit_loss_dict(raw_data, organisation, from_date, to_date, periods=12):
    """
    Parse a Xero Profit and Loss response (dict as returned by serialize_model).
    
    Args:
        raw_data: Dictionary containing the Xero P&L report
        organisation: XeroTenant instance
        from_date: Start date of the report period
        to_date: End date of the report period
        periods: Number of periods (default 12 for monthly)
    
    Returns:
        list: Parsed line items with period values
    """
    if not isinstance(raw_data, dict):
        raise ValueError("raw_data must be a dict containing the Xero P&L report")
    
    reports = raw_data.get("Reports", [])
    if not reports:
        logger.warning("No 'Reports' key in P&L raw_data")
        return [], []
    
    report = reports[0]
    rows = report.get("Rows") or []
    logger.info(f"Found {len(rows)} top-level rows in P&L report")
    
    # Extract period dates from report titles or calculate from from_date/to_date
    # ReportTitles format: ["Profit & Loss", "Company Name", "1 February 2018 to 28 February 2018"]
    report_titles = report.get("ReportTitles", [])
    period_dates = _calculate_period_dates(from_date, to_date, periods)
    
    parsed_rows = []
    
    def safe_decimal(value):
        """Safely convert value to Decimal."""
        if value in (None, "", 0, "0"):
            return Decimal("0")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")
    
    def walk_rows(row_list, section_title="", depth=0):
        """Recursively walk through rows and extract data."""
        for row in row_list:
            row_type = row.get("RowType", "")
            cells = row.get("Cells", [])
            
            # Handle sections
            if row_type == "Section":
                current_section = row.get("Title", section_title)
                nested_rows = row.get("Rows", [])
                logger.debug(f"Found Section '{current_section}' with {len(nested_rows)} nested rows at depth {depth}")
                if nested_rows:
                    walk_rows(nested_rows, current_section, depth + 1)
                continue
            
            # Skip headers (they don't have account data)
            if row_type == "Header":
                continue
            
            # Handle nested rows (for rows that have nested structure)
            # Note: In Xero P&L, only Sections should have nested rows, but we handle it anyway
            nested = row.get("Rows")
            if nested:
                logger.debug(f"Found nested rows in {row_type} row at depth {depth}")
                walk_rows(nested, section_title, depth + 1)
                # If this row has nested rows, it's likely a container and doesn't have its own data
                # But we'll still process it if it's a Row/SummaryRow type (shouldn't happen in Xero P&L)
            
            # Process data rows
            if row_type in ["Row", "SummaryRow"]:
                if not cells:
                    logger.debug(f"Skipping {row_type} row with no cells at depth {depth}")
                    continue
                
                # Extract account information from first cell
                account_name = None
                account_code = None
                account_id_uuid = None
                account_type = None
                
                first_cell = cells[0] if cells else {}
                account_name = str(first_cell.get("Value", "")).strip()
                
                # Check for account attributes in first cell
                attrs = first_cell.get("Attributes", [])
                for attr in attrs:
                    attr_id = attr.get("Id", "")
                    attr_val = attr.get("Value", "")
                    if attr_id == "account":
                        account_id_uuid = attr_val
                    elif attr_id == "accountcode":
                        account_code = attr_val
                    elif attr_id == "accounttype":
                        account_type = attr_val
                
                # Try to find account by UUID or name
                account = None
                if account_id_uuid:
                    try:
                        account = XeroAccount.objects.get(
                            organisation=organisation,
                            account_id=account_id_uuid
                        )
                        account_code = account.code
                        account_type = account.type
                    except XeroAccount.DoesNotExist:
                        logger.debug(f"Account with UUID {account_id_uuid} not found in database")
                        pass
                
                # Extract period values (skip first cell which is account name)
                period_values = {}
                for i, cell in enumerate(cells[1:], start=0):
                    cell_value = cell.get("Value", "")
                    period_values[f'period_{i}'] = str(safe_decimal(cell_value))
                
                logger.debug(f"Parsing {row_type} row: '{account_name}' with {len(period_values)} periods, account_code={account_code}")
                
                # Always create line if we have account name (even if empty, for summary rows)
                # This ensures we capture all rows including summary rows and totals
                parsed_rows.append({
                    'account': account,
                    'account_code': account_code or '',
                    'account_name': account_name,
                    'account_type': account_type,
                    'row_type': row_type,
                    'section_title': section_title,
                    'period_values': period_values,
                    'raw_row': row
                })
    
    # Start parsing
    walk_rows(rows)
    
    logger.info(f"Parsed {len(parsed_rows)} rows from P&L report")
    return parsed_rows, period_dates


def _calculate_period_dates(from_date, to_date, periods):
    """
    Calculate period dates for monthly periods.
    
    Returns:
        list: List of date objects representing the start of each period
    """
    period_dates = []
    current_date = from_date
    
    # Calculate period length
    total_days = (to_date - from_date).days
    period_days = total_days / periods
    
    for i in range(periods):
        period_dates.append(current_date)
        # Move to next period (approximately monthly)
        if i < periods - 1:
            # Add one month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
    
    return period_dates


def parse_profit_loss_report(organisation, data, from_date, to_date, periods=12):
    """
    Parse and create a Profit and Loss report from Xero API data.
    
    Args:
        organisation: XeroTenant instance
        data: Dictionary containing the Xero P&L report
        from_date: Start date of the report period
        to_date: End date of the report period
        periods: Number of periods (default 12)
    
    Returns:
        XeroProfitAndLossReport instance
    """
    # Check if report already exists
    existing_report = XeroProfitAndLossReport.objects.filter(
        organisation=organisation,
        from_date=from_date,
        to_date=to_date,
        periods=periods
    ).first()
    
    if existing_report:
        logger.info(f"P&L report already exists for {from_date} to {to_date}, returning existing report")
        return existing_report
    
    # Create report
    report = XeroProfitAndLossReport.objects.create(
        organisation=organisation,
        from_date=from_date,
        to_date=to_date,
        periods=periods,
        timeframe='MONTH',
        raw_data=data
    )
    
    # Parse and create lines
    parsed_rows, period_dates = parse_profit_loss_dict(data, organisation, from_date, to_date, periods)
    
    lines_created = 0
    for row_data in parsed_rows:
        XeroProfitAndLossReportLine.objects.create(
            report=report,
            account=row_data['account'],
            account_code=row_data['account_code'],
            account_name=row_data['account_name'],
            account_type=row_data['account_type'],
            row_type=row_data['row_type'],
            section_title=row_data['section_title'],
            period_values=row_data['period_values'],
            raw_cell_data={'row': row_data['raw_row']}
        )
        lines_created += 1
    
    logger.info(f"Created P&L report with {lines_created} lines for {from_date} to {to_date}")
    
    return report

