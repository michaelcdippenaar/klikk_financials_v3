"""
Export services for Trail Balance and Profit & Loss reports.
"""
import csv
import json
import logging
import os

from ..models import XeroTrailBalanceReport, XeroTrailBalanceReportLine, XeroProfitAndLossReport, XeroProfitAndLossReportLine

logger = logging.getLogger(__name__)


def export_all_line_items_to_csv(report_id):
    """
    Export all line items from a trial balance report to CSV.
    
    Args:
        report_id: ID of XeroTrailBalanceReport
    
    Returns:
        dict: File path and export statistics
    """
    try:
        report = XeroTrailBalanceReport.objects.get(id=report_id)
    except XeroTrailBalanceReport.DoesNotExist:
        raise ValueError(f"Report {report_id} not found")
    
    lines = XeroTrailBalanceReportLine.objects.filter(report=report).order_by('account_code', 'id')
    
    # Create export directory if it doesn't exist
    # Save to apps/xero/xero_validation/exports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up to services, then to xero_validation, then to exports
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    export_dir = os.path.join(base_dir, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate filename
    filename = f"trail_balance_report_{report.id}_{report.report_date.strftime('%Y%m%d')}.csv"
    file_path = os.path.join(export_dir, filename)
    
    # Write CSV
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Account Code', 'Account Name', 'Account Type', 'Debit', 'Credit', 'Value', 'Row Type'
        ])
        
        for line in lines:
            writer.writerow([
                line.account_code,
                line.account_name,
                line.account.type if line.account else '',
                str(line.debit),
                str(line.credit),
                str(line.value),
                line.row_type or ''
            ])
    
    return {
        'success': True,
        'file_path': file_path,
        'filename': filename,
        'lines_exported': lines.count()
    }


def export_trail_balance_report_complete(report_id):
    """
    Export Trail Balance report: both raw JSON and parsed lines to files.
    
    Args:
        report_id: ID of XeroTrailBalanceReport
    
    Returns:
        dict: File paths and export statistics
    """
    print("[PROCESS] export_trail_balance")
    
    try:
        report = XeroTrailBalanceReport.objects.get(id=report_id)
    except XeroTrailBalanceReport.DoesNotExist:
        raise ValueError(f"Report {report_id} not found")
    
    # Create export directory if it doesn't exist
    # Save to apps/xero/xero_validation/exports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    export_dir = os.path.join(base_dir, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    date_str = report.report_date.strftime('%Y%m%d')
    prefix = f"trail_balance_report_{report.id}_{date_str}"
    
    # 1. Export raw JSON data
    raw_filename = f"{prefix}_raw.json"
    raw_file_path = os.path.join(export_dir, raw_filename)
    
    with open(raw_file_path, 'w', encoding='utf-8') as f:
        json.dump(report.raw_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Exported raw Trail Balance data to {raw_file_path}")
    
    # 2. Export parsed report lines to CSV
    lines = XeroTrailBalanceReportLine.objects.filter(report=report).order_by('account_code', 'id')
    lines_filename = f"{prefix}_lines.csv"
    lines_file_path = os.path.join(export_dir, lines_filename)
    
    with open(lines_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Account Code', 'Account Name', 'Account Type', 'Account ID',
            'Debit', 'Credit', 'Value', 
            'Period Debit', 'Period Credit',
            'YTD Debit', 'YTD Credit',
            'DB Value', 'Row Type'
        ])
        
        for line in lines:
            writer.writerow([
                line.account_code or '',
                line.account_name or '',
                line.account.type if line.account else '',
                line.account.account_id if line.account else '',
                str(line.debit),
                str(line.credit),
                str(line.value),
                str(line.period_debit),
                str(line.period_credit),
                str(line.ytd_debit),
                str(line.ytd_credit),
                str(line.db_value) if line.db_value is not None else '',
                line.row_type or ''
            ])
    
    logger.info(f"Exported {lines.count()} Trail Balance lines to {lines_file_path}")
    
    return {
        'success': True,
        'report_id': report.id,
        'report_date': report.report_date.isoformat(),
        'raw_json_file': {
            'filename': raw_filename,
            'file_path': raw_file_path
        },
        'lines_csv_file': {
            'filename': lines_filename,
            'file_path': lines_file_path,
            'lines_exported': lines.count()
        },
        'export_dir': export_dir
    }


def export_profit_loss_report_complete(report_id):
    """
    Export Profit and Loss report: both raw JSON and parsed lines to files.
    
    Args:
        report_id: ID of XeroProfitAndLossReport
    
    Returns:
        dict: File paths and export statistics
    """
    print("[PROCESS] export_profit_loss")
    
    try:
        report = XeroProfitAndLossReport.objects.get(id=report_id)
    except XeroProfitAndLossReport.DoesNotExist:
        raise ValueError(f"P&L Report {report_id} not found")
    
    # Create export directory if it doesn't exist
    # Save to apps/xero/xero_validation/exports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    export_dir = os.path.join(base_dir, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    date_str = f"{report.from_date.strftime('%Y%m%d')}_to_{report.to_date.strftime('%Y%m%d')}"
    prefix = f"profit_loss_report_{report.id}_{date_str}"
    
    # 1. Export raw JSON data
    raw_filename = f"{prefix}_raw.json"
    raw_file_path = os.path.join(export_dir, raw_filename)
    
    with open(raw_file_path, 'w', encoding='utf-8') as f:
        json.dump(report.raw_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Exported raw P&L data to {raw_file_path}")
    
    # 2. Export parsed report lines to CSV
    lines = XeroProfitAndLossReportLine.objects.filter(report=report).order_by('section_title', 'account_code', 'id')
    lines_filename = f"{prefix}_lines.csv"
    lines_file_path = os.path.join(export_dir, lines_filename)
    
    # Determine number of periods from first line (or use report.periods)
    num_periods = report.periods
    period_headers = [f'Period_{i}' for i in range(num_periods)]
    
    with open(lines_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header row: basic fields + period columns
        header = [
            'Section Title', 'Account Code', 'Account Name', 'Account Type', 'Account ID',
            'Row Type'
        ] + period_headers
        writer.writerow(header)
        
        for line in lines:
            row = [
                line.section_title or '',
                line.account_code or '',
                line.account_name or '',
                line.account_type or '',
                line.account.account_id if line.account else '',
                line.row_type or ''
            ]
            
            # Add period values
            for i in range(num_periods):
                period_key = f'period_{i}'
                value = line.period_values.get(period_key, '0')
                row.append(str(value))
            
            writer.writerow(row)
    
    logger.info(f"Exported {lines.count()} P&L lines to {lines_file_path}")
    
    return {
        'success': True,
        'report_id': report.id,
        'from_date': report.from_date.isoformat(),
        'to_date': report.to_date.isoformat(),
        'periods': report.periods,
        'raw_json_file': {
            'filename': raw_filename,
            'file_path': raw_file_path
        },
        'lines_csv_file': {
            'filename': lines_filename,
            'file_path': lines_file_path,
            'lines_exported': lines.count()
        },
        'export_dir': export_dir
    }


def export_report_to_files(report_id, output_dir=None):
    """
    Export a trail balance report to CSV and JSON files.
    
    Args:
        report_id: ID of XeroTrailBalanceReport
        output_dir: Optional output directory (deprecated - now uses helpers/exports)
    
    Returns:
        dict: File paths and export statistics
    """
    # Use the new complete export function
    return export_trail_balance_report_complete(report_id)

