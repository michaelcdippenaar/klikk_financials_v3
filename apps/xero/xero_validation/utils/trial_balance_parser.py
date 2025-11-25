import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.utils import timezone
from django.db.models import Sum, Q

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_core.services import XeroApiClient, XeroAccountingApi, serialize_model
from apps.xero.xero_metadata.models import XeroAccount
from apps.xero.xero_cube.models import XeroTrailBalance
from ..models import XeroTrailBalanceReport, XeroTrailBalanceReportLine, TrailBalanceComparison

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core parser for Xero Trial Balance JSON
# ---------------------------------------------------------------------------

def parse_trial_balance_dict(raw_data):
    """
    Parse a Xero Trial Balance response (dict as returned by serialize_model).

    Returns a list of dicts with:
        - account_id_uuid
        - account_code
        - account_name
        - account_type
        - debit
        - credit
        - ytd_debit
        - ytd_credit
        - value (debit - credit)
        - row_type
        - raw_row  (original row struct)
    """
    if not isinstance(raw_data, dict):
        raise ValueError("raw_data must be a dict containing the Xero trial balance report")

    reports = raw_data.get("Reports", [])
    if not reports:
        logger.warning("No 'Reports' key in trial balance raw_data")
        return []

    report = reports[0]
    rows = report.get("Rows") or []

    parsed_rows = []

    def safe_decimal(value):
        if value in (None, "", 0, "0"):
            return Decimal("0")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def walk_rows(row_list, depth=0):
        for row in row_list:
            row_type = row.get("RowType", "")
            
            # Check for nested rows first (Sections, SummaryRows, etc. can have nested Rows)
            nested = row.get("Rows")
            if nested:
                # Recurse into nested rows (this handles Sections with nested Rows)
                walk_rows(nested, depth + 1)
                # After recursing, continue to next row (Sections don't have account data themselves)
                continue
            
            # Skip Header rows (they don't have account data)
            if row_type == "Header":
                continue
            
            # We only care about actual data rows (Row or SummaryRow)
            if row_type not in ("Row", "SummaryRow"):
                continue

            cells = row.get("Cells") or []
            if not cells:
                logger.debug(f"Skipping {row_type} row with no cells at depth {depth}")
                continue

            # ------------------------------------------------------------------
            # Extract account name, code, uuid, type from Cells / Attributes
            # ------------------------------------------------------------------
            account_name = None
            account_code = None
            account_id_uuid = None
            account_type = None

            for i, cell in enumerate(cells):
                cell_value = cell.get("Value", "")
                attrs = cell.get("Attributes") or []

                # first cell is usually the account name
                if i == 0 and cell_value:
                    account_name = str(cell_value).strip()

                # attributes contain account GUID, code, type, etc.
                for attr in attrs:
                    attr_id = attr.get("Id", "")
                    attr_val = attr.get("Value", "")

                    if not attr_val:
                        continue

                    if attr_id == "account":
                        account_id_uuid = str(attr_val).strip()
                    elif attr_id == "code":
                        account_code = str(attr_val).strip()
                    elif attr_id == "type":
                        account_type = str(attr_val).strip()

            # Fallback: extract code from "Name (CODE)" pattern in the name, if no code attribute
            if account_name and not account_code:
                m = re.search(r"\(([^)]+)\)\s*$", account_name)
                if m:
                    potential_code = m.group(1).strip()
                    clean_name = re.sub(r"\s*\([^)]+\)\s*$", "", account_name).strip()
                    if clean_name:
                        account_name = clean_name
                    account_code = potential_code

            # ------------------------------------------------------------------
            # Filter out non-account / total rows
            # ------------------------------------------------------------------

            # Skip rows that clearly aren't accounts: no uuid and no code
            # BUT: Allow SummaryRow types even without account info (they might be section totals)
            if row_type == "Row" and not (account_id_uuid or account_code):
                # This will drop things like report titles, etc.
                logger.debug(f"Skipping Row without account info: {account_name}")
                continue
            
            # For SummaryRow, check if it's a total row (skip those)
            if row_type == "SummaryRow":
                first_cell_val = (cells[0].get("Value") or "").strip()
                if first_cell_val.lower().startswith("total ") or not (account_id_uuid or account_code):
                    logger.debug(f"Skipping SummaryRow total: {first_cell_val}")
                    continue

            # ------------------------------------------------------------------
            # Extract numeric values by column position
            # Xero Trial Balance header structure (confirmed from raw data):
            # [0] Account | [1] Debit (Period) | [2] Credit (Period) | [3] YTD Debit | [4] YTD Credit
            # 
            # Example: "Electrical Equipment - @ cost (722)"
            #   - cells[1] = "0.00" (Period Debit)
            #   - cells[2] = "" (Period Credit, empty)
            #   - cells[3] = "905058.20" (YTD Debit) ← Primary value for comparison
            #   - cells[4] = "" (YTD Credit, empty)
            # ------------------------------------------------------------------
            period_debit = safe_decimal(cells[1].get("Value")) if len(cells) > 1 else Decimal("0")
            period_credit = safe_decimal(cells[2].get("Value")) if len(cells) > 2 else Decimal("0")
            ytd_debit = safe_decimal(cells[3].get("Value")) if len(cells) > 3 else Decimal("0")  # YTD Debit column
            ytd_credit = safe_decimal(cells[4].get("Value")) if len(cells) > 4 else Decimal("0")  # YTD Credit column

            # For trial balance, use YTD values as primary (cumulative balances)
            # Fall back to period values if YTD is zero/empty
            # This handles cases where individual accounts only have YTD values
            if ytd_debit or ytd_credit:
                # Use YTD values (cumulative)
                debit = ytd_debit
                credit = ytd_credit
                value = debit - credit
            else:
                # Fall back to period values if YTD not available
                debit = period_debit
                credit = period_credit
                value = debit - credit

            # Skip rows with absolutely no numeric signal (extreme safety)
            if not (debit or credit or period_debit or period_credit or ytd_debit or ytd_credit or value):
                continue

            parsed_rows.append(
                {
                    "account_id_uuid": account_id_uuid,
                    "account_code": account_code or "",
                    "account_name": account_name or "",
                    "account_type": account_type,
                    "debit": debit,  # Primary: YTD if available, else period
                    "credit": credit,  # Primary: YTD if available, else period
                    "period_debit": period_debit,  # Period-only values
                    "period_credit": period_credit,  # Period-only values
                    "ytd_debit": ytd_debit,  # YTD values
                    "ytd_credit": ytd_credit,  # YTD values
                    "value": value,  # Primary: calculated from debit - credit
                    "row_type": row_type,
                    "raw_row": row,
                }
            )

    walk_rows(rows, depth=0)
    logger.info("Parsed %d trial balance data rows from raw_data", len(parsed_rows))
    
    # Debug: Log first few parsed rows if any
    if parsed_rows:
        logger.debug(f"Sample parsed rows (first 3): {parsed_rows[:3]}")
    else:
        logger.warning("No rows parsed from trial balance! Check raw_data structure.")
        # Debug: Log structure of first few rows
        if rows:
            logger.debug(f"First row structure: RowType={rows[0].get('RowType')}, has_Rows={bool(rows[0].get('Rows'))}, has_Cells={bool(rows[0].get('Cells'))}")
            if rows[0].get('Rows'):
                nested = rows[0].get('Rows')
                logger.debug(f"First nested row: RowType={nested[0].get('RowType') if nested else 'None'}, has_Cells={bool(nested[0].get('Cells')) if nested else False}")
    
    return parsed_rows


def export_parsed_data_to_files(raw_data, parsed_rows, output_dir=None, prefix="trial_balance"):
    """
    Export raw data and parsed data to JSON files for testing/debugging.
    
    Args:
        raw_data: The raw JSON data from Xero API
        parsed_rows: The parsed rows from parse_trial_balance_dict
        output_dir: Directory to save files (defaults to current directory)
        prefix: Prefix for filenames (default: "trial_balance")
    
    Returns:
        dict: Paths to the exported files
    """
    if output_dir is None:
        output_dir = os.getcwd()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Convert Decimal to string for JSON serialization
    def decimal_to_str(obj):
        """Recursively convert Decimal to string for JSON serialization"""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_str(item) for item in obj]
        return obj
    
    # Export raw data
    raw_file_path = os.path.join(output_dir, f"{prefix}_raw_{timestamp}.json")
    with open(raw_file_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Exported raw data to {raw_file_path}")
    
    # Export parsed data (convert Decimals to strings)
    parsed_data_serializable = decimal_to_str(parsed_rows)
    parsed_file_path = os.path.join(output_dir, f"{prefix}_parsed_{timestamp}.json")
    with open(parsed_file_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_data_serializable, f, indent=2, ensure_ascii=False)
    logger.info(f"Exported parsed data ({len(parsed_rows)} rows) to {parsed_file_path}")
    
    # Export summary statistics
    summary = {
        "export_timestamp": timestamp,
        "total_rows": len(parsed_rows),
        "rows_with_account_uuid": sum(1 for r in parsed_rows if r.get("account_id_uuid")),
        "rows_with_account_code": sum(1 for r in parsed_rows if r.get("account_code")),
        "rows_with_values": sum(1 for r in parsed_rows if r.get("debit") or r.get("credit")),
        "total_debit": str(sum(r.get("debit", Decimal("0")) for r in parsed_rows)),
        "total_credit": str(sum(r.get("credit", Decimal("0")) for r in parsed_rows)),
        "total_value": str(sum(r.get("value", Decimal("0")) for r in parsed_rows)),
        "file_paths": {
            "raw_data": raw_file_path,
            "parsed_data": parsed_file_path
        }
    }
    
    summary_file_path = os.path.join(output_dir, f"{prefix}_summary_{timestamp}.json")
    with open(summary_file_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"Exported summary to {summary_file_path}")
    
    return {
        "raw_data_file": raw_file_path,
        "parsed_data_file": parsed_file_path,
        "summary_file": summary_file_path,
        "summary": summary
    }


def parse_trial_balance_report(report):
    """
    Use report.raw_data (stored Xero JSON) to recreate XeroTrailBalanceReportLine rows.

    This:
        * Deletes existing lines for the report
        * Parses raw_data using parse_trial_balance_dict
        * Resolves XeroAccount records
        * Creates XeroTrailBalanceReportLine for each parsed row

    Returns:
        dict with stats: lines_created, rows_processed, rows_skipped
    """
    if not report.raw_data:
        raise ValueError("Report has no raw_data to parse")

    organisation = report.organisation

    # Clear existing lines
    deleted = report.lines.all().delete()[0]
    if deleted:
        logger.info("Deleted %d existing lines for report %s", deleted, report.id)

    parsed_rows = parse_trial_balance_dict(report.raw_data)

    lines_created = 0
    rows_processed = 0
    rows_skipped = 0

    for row in parsed_rows:
        rows_processed += 1

        account = None

        # 1) Try uuid first (most reliable)
        if row["account_id_uuid"]:
            try:
                account = XeroAccount.objects.get(
                    organisation=organisation,
                    account_id=row["account_id_uuid"],
                )
            except XeroAccount.DoesNotExist:
                account = None
            except XeroAccount.MultipleObjectsReturned:
                account = (
                    XeroAccount.objects.filter(
                        organisation=organisation,
                        account_id=row["account_id_uuid"],
                    )
                    .order_by("pk")
                    .first()
                )

        # 2) Fallback to account code
        if not account and row["account_code"]:
            # exact code
            try:
                account = XeroAccount.objects.get(
                    organisation=organisation,
                    code=row["account_code"],
                )
            except XeroAccount.DoesNotExist:
                # case-insensitive fallback
                account = (
                    XeroAccount.objects.filter(
                        organisation=organisation,
                        code__iexact=row["account_code"].strip(),
                    )
                    .order_by("pk")
                    .first()
                )
            except XeroAccount.MultipleObjectsReturned:
                account = (
                    XeroAccount.objects.filter(
                        organisation=organisation,
                        code=row["account_code"],
                    )
                    .order_by("pk")
                    .first()
                )

        if not account:
            # We still store the line with account=None (for debugging),
            # but compare_trail_balance will skip these since it checks `if not line.account: continue`
            rows_skipped += 1
            logger.debug(
                "No matching XeroAccount for code=%s, uuid=%s, name=%s",
                row["account_code"],
                row["account_id_uuid"],
                row["account_name"],
            )

        # Use account type from linked account if available, otherwise use parsed type
        final_account_type = row.get("account_type") or (account.type if account else None) or ""
        
        XeroTrailBalanceReportLine.objects.create(
            report=report,
            account=account,
            account_code=row["account_code"],
            account_name=row["account_name"],
            account_type=final_account_type,
            debit=row["debit"],  # Primary: YTD if available, else period
            credit=row["credit"],  # Primary: YTD if available, else period
            value=row["value"],
            period_debit=row.get("period_debit", Decimal("0")),
            period_credit=row.get("period_credit", Decimal("0")),
            ytd_debit=row.get("ytd_debit", Decimal("0")),
            ytd_credit=row.get("ytd_credit", Decimal("0")),
            row_type=row["row_type"],
            raw_cell_data={"row": row["raw_row"]},
        )
        lines_created += 1

        if lines_created <= 5:  # small sample for debug
            logger.debug(
                "Created TB line %d: code=%s, name=%s, debit=%s, credit=%s, value=%s, account_id=%s",
                lines_created,
                row["account_code"],
                row["account_name"],
                row["debit"],
                row["credit"],
                row["value"],
                account.id if account else None,
            )

    logger.info(
        "Trial balance report %s parsed: processed=%d, created=%d, unresolved=%d",
        report.id,
        rows_processed,
        lines_created,
        rows_skipped,
    )

    return {
        "lines_created": lines_created,
        "rows_processed": rows_processed,
        "rows_skipped": rows_skipped,
    }

