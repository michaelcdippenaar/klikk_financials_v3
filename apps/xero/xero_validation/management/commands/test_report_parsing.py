"""
Management command to test raw report file parsing vs parsed lines.
Compares raw JSON report data with database report lines.
"""
import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.xero.xero_validation.models import XeroTrailBalanceReport, XeroTrailBalanceReportLine, XeroProfitAndLossReport, XeroProfitAndLossReportLine
from apps.xero.xero_validation.helpers.trial_balance_parser import parse_trial_balance_dict
from apps.xero.xero_validation.helpers.profit_loss_parser import parse_profit_loss_dict


class Command(BaseCommand):
    help = 'Test raw report file parsing vs parsed database lines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--report-id',
            type=int,
            help='Report ID to test (Trail Balance or P&L)',
        )
        parser.add_argument(
            '--report-type',
            type=str,
            choices=['trail_balance', 'profit_loss', 'auto'],
            default='auto',
            help='Type of report to test (default: auto-detect)',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to raw JSON file to test (optional, uses report.raw_data if not provided)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed comparison results',
        )
        parser.add_argument(
            '--reparse',
            action='store_true',
            help='Re-parse the report and create missing lines (requires --report-id)',
        )

    def handle(self, *args, **options):
        report_id = options.get('report_id')
        report_type = options.get('report_type')
        file_path = options.get('file')
        verbose = options.get('verbose', False)
        reparse = options.get('reparse', False)

        if reparse and not report_id:
            self.stdout.write(self.style.ERROR('--reparse requires --report-id'))
            return

        if not report_id and not file_path:
            self.stdout.write(self.style.ERROR('Either --report-id or --file must be provided'))
            return

        if report_id:
            if reparse:
                self.reparse_report(report_id, report_type, verbose)
            else:
                self.test_report_by_id(report_id, report_type, verbose)
        elif file_path:
            self.test_file(file_path, report_type, verbose)

    def test_report_by_id(self, report_id, report_type, verbose):
        """Test a report by its database ID."""
        self.stdout.write(self.style.SUCCESS(f'\n=== Testing Report ID: {report_id} ===\n'))

        # Try Trail Balance first
        try:
            report = XeroTrailBalanceReport.objects.get(id=report_id)
            self.stdout.write(f'Found Trail Balance Report: {report.report_date}')
            self.test_trail_balance_report(report, verbose)
            return
        except XeroTrailBalanceReport.DoesNotExist:
            pass

        # Try P&L
        try:
            report = XeroProfitAndLossReport.objects.get(id=report_id)
            self.stdout.write(f'Found P&L Report: {report.from_date} to {report.to_date}')
            self.test_profit_loss_report(report, verbose)
            return
        except XeroProfitAndLossReport.DoesNotExist:
            pass

        self.stdout.write(self.style.ERROR(f'Report ID {report_id} not found'))

    def reparse_report(self, report_id, report_type, verbose):
        """Re-parse an existing report and create missing lines."""
        self.stdout.write(self.style.SUCCESS(f'\n=== Re-parsing Report ID: {report_id} ===\n'))

        # Try Trail Balance first
        try:
            report = XeroTrailBalanceReport.objects.get(id=report_id)
            self.stdout.write(f'Found Trail Balance Report: {report.report_date}')
            self.stdout.write(f'Current database lines: {report.lines.count()}')
            
            if not report.raw_data:
                self.stdout.write(self.style.ERROR('Report has no raw_data to parse'))
                return

            # Re-parse using the helper
            from apps.xero.xero_validation.helpers.trial_balance_parser import parse_trial_balance_report
            
            self.stdout.write('Re-parsing report...')
            parse_stats = parse_trial_balance_report(report)
            
            lines_created = parse_stats.get('lines_created', 0)
            rows_processed = parse_stats.get('rows_processed', 0)
            rows_skipped = parse_stats.get('rows_skipped', 0)
            
            self.stdout.write(f'\n=== Re-parsing Results ===')
            self.stdout.write(f'Rows processed: {rows_processed}')
            self.stdout.write(f'Lines created: {lines_created}')
            self.stdout.write(f'Rows skipped (no account match): {rows_skipped}')
            self.stdout.write(f'New total database lines: {report.lines.count()}')
            
            if lines_created > 0:
                self.stdout.write(self.style.SUCCESS(f'✓ Successfully created {lines_created} report lines'))
            else:
                self.stdout.write(self.style.WARNING('⚠ No new lines created. Check if accounts exist in database.'))
            
            return
        except XeroTrailBalanceReport.DoesNotExist:
            pass

        # Try P&L
        try:
            report = XeroProfitAndLossReport.objects.get(id=report_id)
            self.stdout.write(f'Found P&L Report: {report.from_date} to {report.to_date}')
            self.stdout.write(f'Current database lines: {report.lines.count()}')
            
            if not report.raw_data:
                self.stdout.write(self.style.ERROR('Report has no raw_data to parse'))
                return

            # Re-parse P&L
            from apps.xero.xero_validation.helpers.profit_loss_parser import parse_profit_loss_dict
            
            self.stdout.write('Re-parsing P&L report...')
            parsed_rows, period_dates = parse_profit_loss_dict(
                report.raw_data,
                report.organisation,
                report.from_date,
                report.to_date,
                report.periods
            )
            
            # Delete existing lines and recreate
            deleted = report.lines.all().delete()[0]
            self.stdout.write(f'Deleted {deleted} existing lines')
            
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
                
                if lines_created % 20 == 0:
                    self.stdout.write(f'Created {lines_created} lines...')
            
            self.stdout.write(f'\n=== Re-parsing Results ===')
            self.stdout.write(f'Lines created: {lines_created}')
            self.stdout.write(f'New total database lines: {report.lines.count()}')
            
            if lines_created > 0:
                self.stdout.write(self.style.SUCCESS(f'✓ Successfully created {lines_created} report lines'))
            
            return
        except XeroProfitAndLossReport.DoesNotExist:
            pass

        self.stdout.write(self.style.ERROR(f'Report ID {report_id} not found'))

    def test_file(self, file_path, report_type, verbose):
        """Test a raw JSON file."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n=== Testing File: {file_path} ===\n'))

        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        if report_type == 'auto':
            # Auto-detect report type
            reports = raw_data.get('Reports', [])
            if reports:
                report_type_name = reports[0].get('ReportType', '')
                if 'TrialBalance' in report_type_name:
                    report_type = 'trail_balance'
                elif 'ProfitAndLoss' in report_type_name or 'Profit' in report_type_name:
                    report_type = 'profit_loss'

        if report_type == 'trail_balance':
            self.test_trail_balance_raw_data(raw_data, verbose)
        elif report_type == 'profit_loss':
            self.stdout.write(self.style.WARNING('P&L file testing requires organisation context. Use --report-id instead.'))
        else:
            self.stdout.write(self.style.ERROR('Could not determine report type. Use --report-type to specify.'))

    def test_trail_balance_report(self, report, verbose):
        """Test Trail Balance report parsing."""
        if not report.raw_data:
            self.stdout.write(self.style.ERROR('Report has no raw_data'))
            return

        # Get database lines
        db_lines = list(report.lines.all().order_by('account_code', 'id'))
        self.stdout.write(f'Database lines: {len(db_lines)}')

        # Parse raw data
        self.stdout.write('Parsing raw data...')
        parsed_rows = parse_trial_balance_dict(report.raw_data)
        self.stdout.write(f'Parsed rows: {len(parsed_rows)}\n')

        # Compare
        self.compare_trail_balance(parsed_rows, db_lines, verbose)

    def test_trail_balance_raw_data(self, raw_data, verbose):
        """Test Trail Balance raw data parsing (no database comparison)."""
        self.stdout.write('Parsing raw data...')
        parsed_rows = parse_trial_balance_dict(raw_data)
        self.stdout.write(f'Parsed rows: {len(parsed_rows)}\n')

        if verbose:
            self.stdout.write('\n=== Parsed Rows Sample (first 10) ===')
            for i, row in enumerate(parsed_rows[:10], 1):
                self.stdout.write(
                    f"{i}. Code: {row.get('account_code', 'N/A')}, "
                    f"Name: {row.get('account_name', 'N/A')[:40]}, "
                    f"Value: {row.get('value', 0)}"
                )

        # Summary statistics
        self.stdout.write('\n=== Parsing Statistics ===')
        self.stdout.write(f'Total parsed rows: {len(parsed_rows)}')
        self.stdout.write(f'Rows with account_code: {sum(1 for r in parsed_rows if r.get("account_code"))}')
        self.stdout.write(f'Rows with account_id_uuid: {sum(1 for r in parsed_rows if r.get("account_id_uuid"))}')
        self.stdout.write(f'Rows with values: {sum(1 for r in parsed_rows if r.get("debit") or r.get("credit"))}')
        
        total_debit = sum(Decimal(str(r.get("debit", 0))) for r in parsed_rows)
        total_credit = sum(Decimal(str(r.get("credit", 0))) for r in parsed_rows)
        self.stdout.write(f'Total Debit: {total_debit}')
        self.stdout.write(f'Total Credit: {total_credit}')
        self.stdout.write(f'Net Value: {total_debit - total_credit}')

    def test_profit_loss_report(self, report, verbose):
        """Test P&L report parsing."""
        if not report.raw_data:
            self.stdout.write(self.style.ERROR('Report has no raw_data'))
            return

        # Get database lines
        db_lines = list(report.lines.all().order_by('section_title', 'account_code', 'id'))
        self.stdout.write(f'Database lines: {len(db_lines)}')

        # Parse raw data
        self.stdout.write('Parsing raw data...')
        parsed_rows, period_dates = parse_profit_loss_dict(
            report.raw_data,
            report.organisation,
            report.from_date,
            report.to_date,
            report.periods
        )
        self.stdout.write(f'Parsed rows: {len(parsed_rows)}\n')

        # Compare
        self.compare_profit_loss(parsed_rows, db_lines, verbose)

    def compare_trail_balance(self, parsed_rows, db_lines, verbose):
        """Compare parsed rows with database lines for Trail Balance."""
        self.stdout.write('\n=== Comparison Results ===\n')

        # Create lookup dictionaries
        parsed_by_code = {r.get('account_code', ''): r for r in parsed_rows if r.get('account_code')}
        parsed_by_uuid = {r.get('account_id_uuid', ''): r for r in parsed_rows if r.get('account_id_uuid')}
        db_by_code = {line.account_code: line for line in db_lines if line.account_code}
        db_by_uuid = {line.account.account_id: line for line in db_lines if line.account and line.account.account_id}

        # Statistics
        parsed_count = len(parsed_rows)
        db_count = len(db_lines)
        matched_count = 0
        mismatched_count = 0
        missing_in_db = 0
        missing_in_parsed = 0

        mismatches = []
        missing_db = []
        missing_parsed = []

        # Compare parsed rows with DB lines
        for parsed_row in parsed_rows:
            code = parsed_row.get('account_code', '')
            uuid = parsed_row.get('account_id_uuid', '')
            
            db_line = None
            if uuid and uuid in db_by_uuid:
                db_line = db_by_uuid[uuid]
            elif code and code in db_by_code:
                db_line = db_by_code[code]

            if db_line:
                # Compare values
                parsed_value = Decimal(str(parsed_row.get('value', 0)))
                db_value = db_line.value
                
                if abs(parsed_value - db_value) < Decimal('0.01'):
                    matched_count += 1
                else:
                    mismatched_count += 1
                    mismatches.append({
                        'code': code,
                        'name': parsed_row.get('account_name', ''),
                        'parsed_value': parsed_value,
                        'db_value': db_value,
                        'difference': parsed_value - db_value
                    })
            else:
                missing_in_db += 1
                missing_db.append({
                    'code': code,
                    'name': parsed_row.get('account_name', ''),
                    'value': parsed_row.get('value', 0)
                })

        # Find DB lines not in parsed
        for db_line in db_lines:
            code = db_line.account_code
            uuid = db_line.account.account_id if db_line.account else None
            
            found = False
            if uuid and uuid in parsed_by_uuid:
                found = True
            elif code and code in parsed_by_code:
                found = True

            if not found:
                missing_in_parsed += 1
                missing_parsed.append({
                    'code': code,
                    'name': db_line.account_name,
                    'value': db_line.value
                })

        # Print results
        self.stdout.write(f'Parsed rows: {parsed_count}')
        self.stdout.write(f'Database lines: {db_count}')
        self.stdout.write(f'Matched: {matched_count}')
        self.stdout.write(f'Mismatched: {mismatched_count}')
        self.stdout.write(f'Missing in DB: {missing_in_db}')
        self.stdout.write(f'Missing in Parsed: {missing_in_parsed}\n')

        if mismatches and verbose:
            self.stdout.write('\n=== Mismatches ===')
            for m in mismatches[:20]:  # Show first 20
                self.stdout.write(
                    f"Code: {m['code']}, Name: {m['name'][:40]}, "
                    f"Parsed: {m['parsed_value']}, DB: {m['db_value']}, "
                    f"Diff: {m['difference']}"
                )
            if len(mismatches) > 20:
                self.stdout.write(f'... and {len(mismatches) - 20} more mismatches')

        if missing_db and verbose:
            self.stdout.write('\n=== Missing in Database ===')
            for m in missing_db[:20]:
                self.stdout.write(f"Code: {m['code']}, Name: {m['name'][:40]}, Value: {m['value']}")
            if len(missing_db) > 20:
                self.stdout.write(f'... and {len(missing_db) - 20} more')

        if missing_parsed and verbose:
            self.stdout.write('\n=== Missing in Parsed Data ===')
            for m in missing_parsed[:20]:
                self.stdout.write(f"Code: {m['code']}, Name: {m['name'][:40]}, Value: {m['value']}")
            if len(missing_parsed) > 20:
                self.stdout.write(f'... and {len(missing_parsed) - 20} more')

        # Summary
        match_percentage = (matched_count / parsed_count * 100) if parsed_count > 0 else 0
        self.stdout.write(f'\n=== Summary ===')
        self.stdout.write(f'Match percentage: {match_percentage:.2f}%')
        
        if matched_count == parsed_count and missing_in_db == 0 and missing_in_parsed == 0:
            self.stdout.write(self.style.SUCCESS('✓ All rows match perfectly!'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Some discrepancies found. Use --verbose for details.'))

    def compare_profit_loss(self, parsed_rows, db_lines, verbose):
        """Compare parsed rows with database lines for P&L."""
        self.stdout.write('\n=== Comparison Results ===\n')

        # Create lookup dictionaries
        parsed_by_code = {r.get('account_code', ''): r for r in parsed_rows if r.get('account_code')}
        db_by_code = {line.account_code: line for line in db_lines if line.account_code}

        parsed_count = len(parsed_rows)
        db_count = len(db_lines)
        matched_count = 0
        mismatched_count = 0
        missing_in_db = 0
        missing_in_parsed = 0

        # Compare by account code
        for parsed_row in parsed_rows:
            code = parsed_row.get('account_code', '')
            if code and code in db_by_code:
                matched_count += 1
            elif code:
                missing_in_db += 1

        for db_line in db_lines:
            code = db_line.account_code
            if code and code not in parsed_by_code:
                missing_in_parsed += 1

        self.stdout.write(f'Parsed rows: {parsed_count}')
        self.stdout.write(f'Database lines: {db_count}')
        self.stdout.write(f'Matched: {matched_count}')
        self.stdout.write(f'Missing in DB: {missing_in_db}')
        self.stdout.write(f'Missing in Parsed: {missing_in_parsed}\n')

        match_percentage = (matched_count / parsed_count * 100) if parsed_count > 0 else 0
        self.stdout.write(f'Match percentage: {match_percentage:.2f}%')

        if matched_count == parsed_count and missing_in_db == 0 and missing_in_parsed == 0:
            self.stdout.write(self.style.SUCCESS('✓ All rows match perfectly!'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Some discrepancies found.'))

