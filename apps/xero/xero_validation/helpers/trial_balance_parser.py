"""
Parser for Xero Trial Balance reports.
Handles nested row structures and extracts account balances.
"""
import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.utils import timezone
from apps.xero.xero_metadata.models import XeroAccount
from ..models import XeroTrailBalanceReport, XeroTrailBalanceReportLine

logger = logging.getLogger(__name__)


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

            # Recurse into nested sections/groups
            nested = row.get("Rows")
            if nested:
                walk_rows(nested, depth + 1)
                continue

            # We only care about actual data rows
            if row_type != "Row":
                continue

            cells = row.get("Cells") or []
            if not cells:
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
            if not (account_id_uuid or account_code):
                # This will drop things like report titles, section totals, etc.
                continue

            # Optionally, skip rows that are labeled as totals in the first cell
            first_cell_val = (cells[0].get("Value") or "").strip()
            if first_cell_val.lower().startswith("total "):
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
    return parsed_rows


def parse_trial_balance_report(report):
    """
    Use report.parsed_json (if available) or report.raw_data to recreate XeroTrailBalanceReportLine rows.

    This:
        * Deletes existing lines for the report
        * Uses parsed_json if available, otherwise parses raw_data using parse_trial_balance_dict
        * Resolves XeroAccount records using UUID and account_code from parsed data
        * Creates XeroTrailBalanceReportLine for each parsed row

    Returns:
        dict with stats: lines_created, rows_processed, rows_skipped
    """
    print(f"[PARSER] Starting report parsing for report ID {report.id}...")

    organisation = report.organisation

    # Clear existing lines
    deleted = report.lines.all().delete()[0]
    if deleted:
        logger.info("Deleted %d existing lines for report %s", deleted, report.id)
        print(f"[PARSER] Deleted {deleted} existing lines")

    # Use parsed_json if available, otherwise parse from raw_data
    if report.parsed_json:
        print(f"[PARSER] Using stored parsed_json data for report {report.id}")
        parsed_rows = report.parsed_json
        # Convert string Decimal values back to Decimal for processing
        from decimal import Decimal
        for row in parsed_rows:
            for key in ['debit', 'credit', 'value', 'period_debit', 'period_credit', 'ytd_debit', 'ytd_credit']:
                if key in row and isinstance(row[key], str):
                    try:
                        row[key] = Decimal(row[key])
                    except (ValueError, TypeError):
                        row[key] = Decimal('0')
    elif report.raw_data:
        print(f"[PARSER] Parsing from raw_data for report {report.id}")
        parsed_rows = parse_trial_balance_dict(report.raw_data)
    else:
        raise ValueError("Report has neither parsed_json nor raw_data to parse")

    print(f"[PARSER] Using {len(parsed_rows)} parsed rows, now creating database records...")

    lines_created = 0
    rows_processed = 0
    rows_skipped = 0

    for idx, row in enumerate(parsed_rows, 1):
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
            try:
                account = XeroAccount.objects.get(
                    organisation=organisation,
                    code=row["account_code"],
                )
            except XeroAccount.DoesNotExist:
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
            debit=row["debit"],
            credit=row["credit"],
            value=row["value"],
            period_debit=row.get("period_debit", Decimal("0")),
            period_credit=row.get("period_credit", Decimal("0")),
            ytd_debit=row.get("ytd_debit", Decimal("0")),
            ytd_credit=row.get("ytd_credit", Decimal("0")),
            row_type=row["row_type"],
            raw_cell_data={"row": row["raw_row"]},
        )
        lines_created += 1

        # Print progress every 20 lines
        if lines_created % 20 == 0:
            print(f"[PARSER] Created {lines_created} report lines...")

        if lines_created <= 5:  # small sample for debug
            logger.debug(
                "Created TB line %d: code=%s, name=%s, debit=%s, credit=%s, value=%s, account_id=%s",
                lines_created,
                row["account_code"],
                row["account_name"],
                row["debit"],
                row["credit"],
                row["value"],
                account.account_id if account else None,
            )

    print(f"[PARSER] Report parsing complete: {lines_created} lines created, {rows_skipped} skipped")

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
