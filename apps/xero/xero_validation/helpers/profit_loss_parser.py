"""
Parser for Xero Profit and Loss reports.
Handles multi-period P&L reports with monthly columns.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
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
    print(f"[PARSER] Starting Profit & Loss parsing for {from_date} to {to_date} ({periods} periods)...")
    
    if not isinstance(raw_data, dict):
        raise ValueError("raw_data must be a dict containing the Xero P&L report")
    
    reports = raw_data.get("Reports", [])
    if not reports:
        logger.warning("No 'Reports' key in P&L raw_data")
        print("[PARSER] ERROR: No 'Reports' key found in raw_data")
        return [], []
    
    report = reports[0]
    rows = report.get("Rows") or []
    print(f"[PARSER] Found {len(rows)} top-level rows to process")
    
    # Extract period dates from report titles or calculate from from_date/to_date
    report_titles = report.get("ReportTitles", [])
    period_dates = _calculate_period_dates(from_date, to_date, periods)
    print(f"[PARSER] Calculated {len(period_dates)} period dates")
    
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
        rows_in_section = 0
        for row in row_list:
            row_type = row.get("RowType", "")
            cells = row.get("Cells", [])
            
            # Handle sections
            if row_type == "Section":
                current_section = row.get("Title", section_title)
                nested_rows = row.get("Rows", [])
                if current_section and depth == 0:
                    print(f"[PARSER] Processing section: {current_section} ({len(nested_rows)} nested rows)")
                logger.debug(f"Found Section '{current_section}' with {len(nested_rows)} nested rows at depth {depth}")
                if nested_rows:
                    nested_count = walk_rows(nested_rows, current_section, depth + 1)
                    rows_in_section += nested_count
                continue
            
            # Skip headers (they don't have account data)
            if row_type == "Header":
                continue
            
            # Handle nested rows (for rows that have nested structure)
            nested = row.get("Rows")
            if nested:
                logger.debug(f"Found nested rows in {row_type} row at depth {depth}")
                nested_count = walk_rows(nested, section_title, depth + 1)
                rows_in_section += nested_count
            
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
                # Xero returns periods in reverse chronological order (latest first)
                # Cell 0 = Account name
                # Cell 1 = Latest period (should be period_{periods-1})
                # Cell 2 = Previous period (should be period_{periods-2})
                # ...
                # Cell N = Oldest period (should be period_0)
                period_values = {}
                period_cells = cells[1:]  # Skip account name cell
                num_periods = len(period_cells)
                
                # Debug: Log cell structure for first few rows
                if len(parsed_rows) < 3:
                    print(f"[PARSER] DEBUG Row {len(parsed_rows)}: {len(cells)} total cells ({num_periods} period cells), account='{account_name}'")
                    for idx, cell in enumerate(period_cells[:min(5, len(period_cells))]):
                        print(f"[PARSER]   Period cell {idx}: Value='{cell.get('Value', '')}'")
                
                # Map periods in reverse order: latest period (cell 0) -> period_{periods-1}, oldest period (cell N-1) -> period_0
                for cell_idx, cell in enumerate(period_cells):
                    cell_value = cell.get("Value", "")
                    decimal_value = safe_decimal(cell_value)
                    # Reverse the index: cell 0 (latest) maps to period_{periods-1}, cell N-1 (oldest) maps to period_0
                    period_idx = num_periods - 1 - cell_idx
                    period_values[f'period_{period_idx}'] = str(decimal_value)
                    # Debug: Log non-zero values
                    if len(parsed_rows) < 3 and decimal_value != Decimal("0"):
                        print(f"[PARSER]   Cell {cell_idx} (latest first) -> Period {period_idx}: {decimal_value}")
                
                # Verify we have the expected number of periods
                expected_periods = periods
                if len(period_values) < expected_periods:
                    logger.warning(
                        f"Row '{account_name}' has {len(period_values)} periods but expected {expected_periods}. "
                        f"Total cells: {len(cells)}, Period cells: {num_periods}"
                    )
                    if len(parsed_rows) < 3:
                        print(f"[PARSER] WARNING: Expected {expected_periods} periods, got {len(period_values)} from {num_periods} cells")
                
                logger.debug(f"Parsing {row_type} row: '{account_name}' with {len(period_values)} periods, account_code={account_code}")
                
                # Always create line if we have account name (even if empty, for summary rows)
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
                rows_in_section += 1
                
                # Print progress every 10 rows
                if len(parsed_rows) % 10 == 0:
                    print(f"[PARSER] Parsed {len(parsed_rows)} P&L rows...")
        
        return rows_in_section
    
    # Start parsing
    total_rows = walk_rows(rows)
    print(f"[PARSER] Completed parsing: {len(parsed_rows)} P&L rows extracted")
    
    logger.info(f"Parsed {len(parsed_rows)} rows from P&L report")
    
    if parsed_rows:
        print(f"[PARSER] Sample accounts: {', '.join([r.get('account_code', r.get('account_name', 'N/A'))[:30] for r in parsed_rows[:3]])}")
    
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
    print(f"[PARSER] Starting P&L report creation for {from_date} to {to_date}...")
    
    # Check if report already exists
    existing_report = XeroProfitAndLossReport.objects.filter(
        organisation=organisation,
        from_date=from_date,
        to_date=to_date,
        periods=periods
    ).first()
    
    if existing_report:
        logger.info(f"P&L report already exists for {from_date} to {to_date}, returning existing report")
        print(f"[PARSER] Report already exists (ID: {existing_report.id}), skipping creation")
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
    print(f"[PARSER] Created report record (ID: {report.id})")
    
    # Parse and create lines
    parsed_rows, period_dates = parse_profit_loss_dict(data, organisation, from_date, to_date, periods)
    print(f"[PARSER] Parsed {len(parsed_rows)} rows from raw data, now creating database records...")
    
    lines_created = 0
    for idx, row_data in enumerate(parsed_rows, 1):
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
        
        # Print progress every 20 lines
        if lines_created % 20 == 0:
            print(f"[PARSER] Created {lines_created} report lines...")
    
    print(f"[PARSER] P&L report creation complete: {lines_created} lines created")
    
    logger.info(f"Created P&L report with {lines_created} lines for {from_date} to {to_date}")
    
    return report

