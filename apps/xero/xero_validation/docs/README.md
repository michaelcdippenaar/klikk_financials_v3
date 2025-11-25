# Xero Validation App Documentation

## Overview

The `xero_validation` app provides comprehensive validation and comparison functionality for Xero financial reports. It imports Trial Balance and Profit & Loss reports from the Xero API, compares them with database values, validates balance sheet accounts, and exports reports in various formats.

## Purpose

The app serves to:
- **Import** financial reports (Trial Balance, Profit & Loss) from Xero API
- **Compare** Xero report values with database-calculated values
- **Validate** balance sheet accounts for accuracy and completeness
- **Export** reports to CSV and JSON formats for analysis
- **Integrate** income statement data into trial balance reports

## Architecture

### Directory Structure

```
xero_validation/
├── views/                    # API view classes
│   ├── __init__.py          # View exports
│   ├── common.py            # Shared view helpers
│   ├── trial_balance_views.py  # Trial Balance API views
│   └── profit_loss_views.py    # Profit & Loss API views
├── services/                 # Business logic layer
│   ├── __init__.py          # Service exports
│   ├── imports.py           # Report import services
│   ├── comparisons.py       # Comparison services
│   ├── validation.py        # Validation services
│   ├── exports.py           # Export services
│   ├── income_statement.py  # Income statement services
│   └── helpers.py           # Service helpers (deprecated, use helpers.service_helpers)
├── helpers/                  # Helper utilities
│   ├── __init__.py
│   ├── trial_balance_parser.py  # Trial Balance parser
│   ├── profit_loss_parser.py    # Profit & Loss parser
│   └── service_helpers.py       # Service utility functions
├── unit_tests/               # Unit tests
│   └── test_trial_balance_uuid_matching.py
├── models.py                 # Django models
├── urls.py                   # URL routing
└── docs/                     # Documentation
    └── README.md            # This file
```

## Models

### XeroTrailBalanceReport
Stores imported Trial Balance reports from Xero API.

**Fields:**
- `organisation`: ForeignKey to XeroTenant
- `report_date`: Date of the report
- `report_type`: Type of report (default: 'TrialBalance')
- `imported_at`: Timestamp when imported
- `raw_data`: Raw JSON from Xero API
- `parsed_json`: Parsed JSON data

### XeroTrailBalanceReportLine
Individual line items from Trial Balance reports.

**Fields:**
- `report`: ForeignKey to XeroTrailBalanceReport
- `account`: ForeignKey to XeroAccount (nullable)
- `account_code`, `account_name`, `account_type`: Account details
- `debit`, `credit`, `value`: Primary amounts (YTD if available, else period)
- `period_debit`, `period_credit`: Period-only amounts
- `ytd_debit`, `ytd_credit`: Year-to-date cumulative amounts
- `db_value`: Database-calculated value
- `row_type`: Row type (Header, Row, SummaryRow)
- `raw_cell_data`: Raw cell data from Xero

### TrailBalanceComparison
Stores comparison results between Xero reports and database.

**Fields:**
- `report`: ForeignKey to XeroTrailBalanceReport
- `account`: ForeignKey to XeroAccount
- `xero_value`: Value from Xero report
- `db_value`: Value from database
- `difference`: Difference (xero_value - db_value)
- `match_status`: Match status (match, mismatch, missing_in_db, missing_in_xero)
- `notes`: Additional notes
- `compared_at`: Timestamp

### XeroProfitAndLossReport
Stores imported Profit & Loss reports from Xero API.

**Fields:**
- `organisation`: ForeignKey to XeroTenant
- `from_date`, `to_date`: Report date range
- `periods`: Number of periods (default: 12)
- `timeframe`: Period type (MONTH, QUARTER, YEAR)
- `imported_at`: Timestamp
- `raw_data`: Raw JSON from Xero API
- `parsed_json`: Parsed JSON data

### XeroProfitAndLossReportLine
Individual line items from P&L reports.

**Fields:**
- `report`: ForeignKey to XeroProfitAndLossReport
- `account`: ForeignKey to XeroAccount (nullable)
- `account_code`, `account_name`: Account details
- `row_type`: Row type
- Period-specific fields: `period_1` through `period_12` (Decimal fields)
- `total`: Total across all periods
- `raw_cell_data`: Raw cell data

## API Endpoints

### Base URL
All endpoints are prefixed with `/xero/validation/`

### Trial Balance Endpoints

#### 1. Validate Balance Sheet Complete
**POST** `/balance-sheet/`

Combined validation endpoint that can run all steps or individual steps.

**Request Body:**
```json
{
  "tenant_id": "string (required)",
  "report_date": "YYYY-MM-DD (optional)",
  "tolerance": "0.01 (optional)",
  "import_trail_balance_only": "false (optional)",
  "compare_only": "false (optional)",
  "validate_only": "false (optional)",
  "export_line_items": "false (optional)",
  "add_income_statement": "false (optional)",
  "target_account_code": "960 (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "message": "string",
  "overall_status": "valid|invalid|partial",
  "report_id": 123,
  "report_date": "YYYY-MM-DD",
  "steps_executed": ["import_trail_balance", "compare", "validate"],
  "stats": {
    "import": {...},
    "compare": {...},
    "validate": {
      "statistics": {
        "missing_accounts": [],
        "missing_transactions": [],
        "amount_mismatches": []
      }
    }
  }
}
```

#### 2. Import Trail Balance
**POST** `/import-trail-balance/` (commented out, use balance-sheet endpoint)

Imports Trial Balance report from Xero API.

#### 3. Compare Trail Balance
**POST** `/compare-trail-balance/` (commented out, use balance-sheet endpoint)

Compares Xero Trial Balance with database values.

#### 4. Export Trail Balance Complete
**POST** `/export-trail-balance/`

Exports Trial Balance report to JSON and CSV files.

**Request Body:**
```json
{
  "report_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "message": "Exported Trail Balance report: 150 lines",
  "report_id": 123,
  "report_date": "YYYY-MM-DD",
  "files_saved_to": "/path/to/exports",
  "raw_json_file": {
    "filename": "trail_balance_123.json",
    "file_path": "/full/path/to/file.json"
  },
  "lines_csv_file": {
    "filename": "trail_balance_lines_123.csv",
    "file_path": "/full/path/to/file.csv",
    "lines_exported": 150
  }
}
```

### Profit & Loss Endpoints

#### 1. Import Profit & Loss
**POST** `/import-profit-loss/`

Imports Profit & Loss report from Xero API.

**Request Body:**
```json
{
  "tenant_id": "string (required)",
  "from_date": "YYYY-MM-DD (required)",
  "to_date": "YYYY-MM-DD (required)",
  "periods": 11 (optional, default: 11 for 12 months),
  "timeframe": "MONTH (optional, default: MONTH)"
}
```

**Response:**
```json
{
  "message": "P&L report imported successfully",
  "report_id": 456,
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD",
  "periods": 12,
  "lines_created": 200,
  "is_new": true
}
```

#### 2. Compare Profit & Loss
**POST** `/compare-profit-loss/`

Compares Xero P&L report with database values (per month for 12-month period).

**Request Body:**
```json
{
  "tenant_id": "string (required)",
  "report_id": 456 (optional),
  "tolerance": "0.01 (optional)"
}
```

**Response:**
```json
{
  "message": "P&L comparison completed",
  "report_id": 456,
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD",
  "periods": 12,
  "period_stats": [
    {
      "period": 1,
      "period_start": "YYYY-MM-DD",
      "period_end": "YYYY-MM-DD",
      "matches": 50,
      "mismatches": 2,
      "missing_in_db": 1,
      "missing_in_xero": 0
    }
  ],
  "overall_statistics": {
    "total_accounts": 53,
    "total_matches": 600,
    "total_mismatches": 24,
    "total_missing_in_db": 12,
    "total_missing_in_xero": 0
  }
}
```

#### 3. Export Profit & Loss Complete
**POST** `/export-profit-loss/`

Exports P&L report to JSON and CSV files.

**Request Body:**
```json
{
  "report_id": 456
}
```

**Response:**
```json
{
  "success": true,
  "message": "Exported P&L report: 200 lines",
  "report_id": 456,
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD",
  "periods": 12,
  "files_saved_to": "/path/to/exports",
  "raw_json_file": {...},
  "lines_csv_file": {...}
}
```

## Services

### Import Services (`services/imports.py`)

#### `import_trail_balance_from_xero(tenant_id, report_date=None, user=None)`
Imports Trial Balance report from Xero API and parses into database.

**Returns:**
- `success`: Boolean
- `message`: Status message
- `report`: XeroTrailBalanceReport instance
- `lines_created`: Number of lines created
- `is_new`: Whether report was newly created

#### `import_profit_loss_from_xero(tenant_id, from_date, to_date, periods=12, timeframe='MONTH', user=None)`
Imports Profit & Loss report from Xero API.

**Returns:**
- `success`: Boolean
- `message`: Status message
- `report`: XeroProfitAndLossReport instance
- `lines_created`: Number of lines created
- `is_new`: Whether report was newly created

### Comparison Services (`services/comparisons.py`)

#### `compare_trail_balance(tenant_id, report_id=None, report_date=None, tolerance=Decimal('0.01'))`
Compares Xero Trial Balance report with database values.

**Returns:**
- `message`: Status message
- `report_id`: Report ID
- `report_date`: Report date
- `statistics`: Comparison statistics

#### `compare_profit_loss(tenant_id, report_id=None, tolerance=Decimal('0.01'))`
Compares Xero P&L report with database values per period.

**Returns:**
- `message`: Status message
- `report_id`: Report ID
- `from_date`, `to_date`: Date range
- `periods`: Number of periods
- `period_stats`: Statistics per period
- `overall_statistics`: Overall statistics

### Validation Services (`services/validation.py`)

#### `validate_balance_sheet_complete(...)`
Combined validation function that can run all steps or individual steps.

**Parameters:**
- `tenant_id`: Xero tenant ID
- `report_date`: Report date (optional)
- `user`: User for authentication (optional)
- `tolerance`: Tolerance for differences (default: 0.01)
- `import_trail_balance_only`: Only import (boolean)
- `compare_only`: Only compare (boolean)
- `validate_only`: Only validate (boolean)
- `export_line_items`: Export to CSV (boolean)
- `add_income_statement`: Add income statement (boolean)
- `target_account_code`: Account code for income statement (default: '960')

**Returns:**
- `success`: Boolean
- `message`: Status message
- `overall_status`: 'valid', 'invalid', or 'partial'
- `report_id`: Report ID
- `report_date`: Report date
- `steps_executed`: List of executed steps
- `stats`: Statistics for each step

#### `validate_balance_sheet_accounts(tenant_id, report_id=None, report_date=None, tolerance=Decimal('0.01'))`
Validates balance sheet accounts from Xero report against database (cumulative YTD).

**Returns:**
- `success`: Boolean
- `overall_status`: Validation status
- `message`: Status message
- `report_id`: Report ID
- `report_date`: Report date
- `statistics`: Validation statistics
- `validations`: List of validation results

### Export Services (`services/exports.py`)

#### `export_trail_balance_report_complete(report_id)`
Exports Trial Balance report: both raw JSON and parsed lines to files.

**Returns:**
- `report_id`: Report ID
- `report_date`: Report date
- `export_dir`: Export directory
- `raw_json_file`: Raw JSON file info
- `lines_csv_file`: Lines CSV file info

#### `export_profit_loss_report_complete(report_id)`
Exports P&L report: both raw JSON and parsed lines to files.

**Returns:**
- `report_id`: Report ID
- `from_date`, `to_date`: Date range
- `periods`: Number of periods
- `export_dir`: Export directory
- `raw_json_file`: Raw JSON file info
- `lines_csv_file`: Lines CSV file info

#### `export_all_line_items_to_csv(report_id)`
Exports all line items from a report to CSV.

**Returns:**
- `file_path`: Full file path
- `filename`: Filename
- `lines_exported`: Number of lines exported

### Income Statement Services (`services/income_statement.py`)

#### `add_income_statement_to_trail_balance_report(report_id=None, tenant_id=None, target_account_code='960')`
Adds income statement (P&L) entries to a Trial Balance report.

**Returns:**
- `message`: Status message
- `lines_created`: Number of lines created
- `pnl_value`: Profit & Loss value
- `revenue_total`: Total revenue
- `expense_total`: Total expenses
- `report_id`: Report ID
- `report_date`: Report date

## Helpers

### Parsers (`helpers/`)

#### `trial_balance_parser.py`
- `parse_trial_balance_dict(raw_data)`: Parse raw Xero Trial Balance JSON
- `parse_trial_balance_report(report)`: Parse report and create lines

#### `profit_loss_parser.py`
- `parse_profit_loss_dict(raw_data, organisation, from_date, to_date, periods=12)`: Parse raw Xero P&L JSON
- `parse_profit_loss_report(organisation, data, from_date, to_date, periods=12)`: Parse report and create lines

### Service Helpers (`helpers/service_helpers.py`)

#### `convert_decimals_to_strings(obj)`
Recursively convert Decimal objects to strings for JSON serialization.

#### `reparse_report_from_raw_data(report_id)`
Re-parse a report from its raw_data field (useful if parsing logic changed).

## Unit Tests

### Location
`unit_tests/test_trial_balance_uuid_matching.py`

### Test Class
`TrialBalanceUUIDMatchingTests`

**Purpose:** Validates that Trial Balance parsing and validation always use UUID (Xero account_id) as the primary key for matching accounts.

**Test Methods:**
- `test_parse_trial_balance_links_by_uuid`: Tests UUID-based account linking
- `test_validation_uses_uuid_for_missing_accounts`: Tests validation uses UUIDs
- Additional tests for account matching logic

### Running Tests
```bash
python manage.py test apps.xero.xero_validation.unit_tests
```

## Flow Diagrams

### Trial Balance Validation Flow

```
1. Import Trail Balance
   ├── Fetch from Xero API
   ├── Parse raw JSON
   ├── Create XeroTrailBalanceReport
   └── Create XeroTrailBalanceReportLine records

2. Compare Trail Balance
   ├── Get report lines
   ├── Calculate database values from XeroTrailBalance
   ├── Compare Xero vs DB values
   └── Create TrailBalanceComparison records

3. Validate Balance Sheet
   ├── Filter balance sheet accounts
   ├── Check for missing accounts
   ├── Check for missing transactions
   ├── Check for amount mismatches
   └── Return validation results

4. Export (Optional)
   ├── Export raw JSON
   └── Export parsed lines to CSV

5. Add Income Statement (Optional)
   ├── Get latest P&L report
   ├── Calculate revenue/expense totals
   └── Add entry to Trial Balance report
```

### Profit & Loss Comparison Flow

```
1. Import P&L Report
   ├── Fetch from Xero API
   ├── Parse raw JSON
   ├── Create XeroProfitAndLossReport
   └── Create XeroProfitAndLossReportLine records (per period)

2. Compare P&L
   ├── For each period:
   │   ├── Get P&L lines for period
   │   ├── Calculate DB values from XeroTrailBalance
   │   ├── Compare Xero vs DB values
   │   └── Record statistics
   └── Calculate overall statistics

3. Export (Optional)
   ├── Export raw JSON
   └── Export parsed lines to CSV
```

## Successful Test Cases

### Test Case 1: Complete Trial Balance Validation
**Input:**
- `tenant_id`: Valid Xero tenant ID
- `report_date`: Current date
- All flags: `false` (run all steps)

**Expected Result:**
- Trial Balance imported successfully
- Comparison completed with statistics
- Validation passed (or shows mismatches)
- Export files created
- Income statement added (if enabled)

**Status:** ✅ Working

### Test Case 2: Import Only
**Input:**
- `tenant_id`: Valid Xero tenant ID
- `import_trail_balance_only`: `true`

**Expected Result:**
- Trial Balance imported
- Report ID returned
- No comparison or validation performed

**Status:** ✅ Working

### Test Case 3: P&L Import and Compare
**Input:**
- `tenant_id`: Valid Xero tenant ID
- `from_date`: Start of fiscal year
- `to_date`: End of fiscal year
- `periods`: 11 (12 months)

**Expected Result:**
- P&L report imported
- Comparison completed per period
- Statistics returned for each period and overall

**Status:** ✅ Working

### Test Case 4: UUID-Based Account Matching
**Input:**
- Trial Balance report with account UUIDs
- Database with matching accounts

**Expected Result:**
- Accounts matched by UUID first
- Fallback to account code if UUID not found
- All accounts properly linked

**Status:** ✅ Tested (unit_tests/test_trial_balance_uuid_matching.py)

## Common Issues and Solutions

### Issue: Missing Accounts in Validation
**Cause:** Account UUID mismatch or account not in database
**Solution:** Ensure accounts are synced from Xero metadata API

### Issue: Amount Mismatches
**Cause:** Different calculation methods or timing differences
**Solution:** Check tolerance settings, verify date ranges match

### Issue: Import Fails
**Cause:** Invalid tenant_id or API authentication issues
**Solution:** Verify tenant_id exists, check Xero API credentials

## Dependencies

- `xero_core`: XeroTenant model, API client services
- `xero_metadata`: XeroAccount model
- `xero_cube`: XeroTrailBalance model (for database calculations)
- `xero_auth`: Authentication and credentials

## Future Enhancements

1. **Real-time Validation**: WebSocket support for live validation updates
2. **Batch Processing**: Support for multiple tenants/periods
3. **Advanced Reporting**: Enhanced comparison reports with visualizations
4. **Automated Reconciliation**: Auto-fix minor discrepancies
5. **Audit Trail**: Track all validation changes and comparisons

## Contributing

When adding new features:
1. Follow the existing structure (views/, services/, helpers/)
2. Add unit tests in `unit_tests/`
3. Update this documentation
4. Ensure backward compatibility for existing APIs

## Version History

- **v3.0**: Reorganized structure, separated views, improved documentation
- **v2.0**: Added P&L support, enhanced validation
- **v1.0**: Initial Trial Balance validation

