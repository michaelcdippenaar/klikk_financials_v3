# Xero Apps Architecture Documentation

This document explains how the monolithic `apps/xero` application has been split into modular, focused Django apps. Each app has a specific responsibility and contains related models, views, services, and business logic.

## Overview

The xero functionality has been split into 8 specialized apps:

1. **xero_auth** - Authentication and OAuth flow
2. **xero_core** - Core tenant model (central reference)
3. **xero_metadata** - Reference data and metadata
4. **xero_data** - Transaction and journal data
5. **xero_sync** - Data synchronization, scheduling, and task execution
6. **xero_cube** - Aggregated data (trail balance, balance sheets)
7. **xero_integration** - External API integration
8. **xero_validation** - Data validation and comparison

---

## 1. xero_auth

**Purpose**: Handles all Xero OAuth authentication, token management, and authorization flows.

### Models
- `XeroClientCredentials` - Stores user's Xero OAuth client credentials (client_id, client_secret, tokens)
- `XeroTenantToken` - Stores tenant-specific OAuth tokens and refresh tokens
- `XeroAuthSettings` - Stores OAuth endpoint URLs (access_token_url, refresh_url, auth_url)

### Functionality
- OAuth 2.0 authentication flow initiation
- OAuth callback handling
- Token refresh logic
- Token storage and management
- User-to-Xero connection management

### Views/Endpoints
- `XeroAuthInitiateView` - Initiates OAuth flow
- `XeroCallbackView` - Handles OAuth callback

### Services
- Token refresh services
- OAuth flow management
- Credential validation

### Dependencies
- Depends on: `xero_core` (for XeroTenant)
- Used by: All other xero apps (for authentication)

---

## 2. xero_core

**Purpose**: Core tenant management and Xero API client layer. This is the central hub that other apps reference. Contains the central tenant model and core API communication services.

### Models
- `XeroTenant` - Central tenant/organization model (tenant_id, tenant_name)

### Functionality
- Tenant/organization management
- Tenant validation
- Central reference point for all other xero apps
- Xero API client communication
- Low-level and high-level API wrappers

### Services
- `XeroApiClient` - Low-level Xero API client
- `XeroAccountingApi` - High-level Xero Accounting API wrapper
- Tenant validation services
- Tenant lookup services
- API request/response handling
- Error handling and retry logic
- Rate limiting

### Views/Endpoints
- `XeroTenantListView` - List all tenants for a user
- Tenant management endpoints

### Dependencies
- Depends on: `apps.user` (for User model), `xero_auth` (for authentication)
- Used by: All other xero apps (central tenant reference and API access)

---

## 3. xero_metadata

**Purpose**: Stores reference data and metadata that doesn't change frequently. This includes accounts, contacts, tracking categories, and business units.

### Models
- `XeroBusinessUnits` - Business unit and division codes/descriptions
- `XeroAccount` - Chart of accounts (account_id, code, name, type, grouping, reporting codes)
- `XeroTracking` - Tracking categories and options
- `XeroContacts` - Contacts (customers, suppliers, employees)

### Functionality
- Reference data management
- Account hierarchy and structure
- Tracking category management
- Contact management
- Business unit mapping

### Custom Managers
- `XeroAccountManager` - Bulk account creation/updates from Xero API
- `XeroTrackingModelManager` - Bulk tracking category creation/updates
- `XeroContactsModelManager` - Bulk contact creation/updates

### Services
- Metadata sync services
- Account validation
- Reference data export

### Dependencies
- Depends on: `xero_core` (for XeroTenant, XeroApiClient, XeroAccountingApi)
- Used by: `xero_data`, `xero_cube`, `xero_sync`

---

## 4. xero_data

**Purpose**: Manages transaction data, journals, and source transactions from Xero.

### Models
- `XeroTransactionSource` - Source transactions (BankTransaction, Invoice, Payment)
- `XeroJournalsSource` - Raw journal entries from Xero API (before processing)
- `XeroJournals` - Processed journal line items with account, date, amount, tracking

### Functionality
- Transaction data storage
- Journal entry processing
- Transaction-to-journal mapping
- Contact linking to transactions
- Tracking category assignment

### Custom Managers
- `XeroTransactionSourceModelManager` - Bulk transaction creation (bank transactions, invoices, payments)
- `XeroJournalsSourceManager` - Journal source processing
- `XeroJournalsManager` - Journal aggregation and account balance calculations

### Services
- Journal processing services
- Transaction validation
- Data transformation logic

### Dependencies
- Depends on: `xero_core` (XeroTenant, XeroApiClient, XeroAccountingApi), `xero_metadata` (XeroAccount, XeroContacts, XeroTracking)
- Used by: `xero_cube` (for aggregation), `xero_sync` (for updates)

---

## 5. xero_sync

**Purpose**: Handles everything related to syncing data from Xero API. This includes data synchronization, scheduling sync tasks, task execution logging, incremental updates, and last-update tracking.

### Models
- `XeroLastUpdate` - Tracks last update timestamp per endpoint per tenant
- `XeroTenantSchedule` - Per-tenant scheduling configuration (update intervals, preferred times, last run times, next run times)
- `XeroTaskExecutionLog` - Logs execution stats for scheduled sync tasks (update_models, process_data)

### Functionality
- Incremental data synchronization
- Last-update tracking per API endpoint
- Sync scheduling and coordination
- Per-tenant schedule configuration
- Task execution logging and monitoring
- Schedule validation and next-run calculation
- Update task execution (`update_xero_models` function)
- Delta/incremental update logic
- Triggering sync operations (scheduled and manual)

### Custom Managers
- `XeroLastUpdateModelManager` - Manages last-update timestamps

### Services
- `update_xero_models()` - Main sync service that fetches data from Xero API
- Sync coordination services
- Schedule management services
- Task execution tracking services
- Incremental update logic

### Views/Endpoints
- `XeroUpdateModelsView` - Manual trigger for data sync

### Dependencies
- Depends on: `xero_core` (XeroTenant, XeroApiClient, XeroAccountingApi), `xero_auth` (for API authentication), `xero_metadata`, `xero_data`
- Used by: Scheduled tasks, manual sync triggers

---

## 6. xero_cube

**Purpose**: Handles aggregated and consolidated data - trail balance and balance sheets. This is the analytical/OLAP layer.

### Models
- `XeroTrailBalance` - Aggregated journal data by account, year, month, contact, tracking
- `XeroBalanceSheet` - Running balance calculations per account/contact over time

### Functionality
- Trail balance consolidation from journals
- Balance sheet calculation (running balances)
- Financial period calculations (fiscal year, financial period)
- Incremental consolidation (only rebuild affected periods)
- Account balance aggregation

### Custom Managers
- `XeroTrailBalanceManager` - Consolidates journals into trail balance
- `XeroBalanceSheetManager` - Creates balance sheet from trail balance

### Services
- `create_trail_balance()` - Consolidation service
- `create_balance_sheet()` - Balance sheet creation service
- `process_xero_data()` - Main processing service that orchestrates consolidation

### Views/Endpoints
- `XeroProcessDataView` - Manual trigger for data processing
- `XeroDataSummaryView` - Data summary/statistics

### Dependencies
- Depends on: `xero_core` (XeroTenant), `xero_data` (XeroJournals), `xero_metadata` (XeroAccount, XeroContacts, XeroTracking)
- Used by: Reporting, analytics, `xero_integration` (for external exports)

---

## 7. xero_integration

**Purpose**: External integrations and data distribution to other systems/apps. Handles exporting data to external services like BigQuery, data warehouses, and other third-party systems.

### Functionality
- BigQuery integration and exports
- Data warehouse integrations
- Third-party system integrations
- Data distribution services
- Export functionality for external consumption
- ETL pipelines to external systems

### Services
- BigQuery export services
- Data warehouse export services
- External system integration services
- Data distribution services

### Dependencies
- Depends on: `xero_core` (for tenant context and data access), `xero_cube` (for aggregated data), `xero_metadata` (for reference data)
- Used by: External systems, data warehouses, reporting tools

---

## 8. xero_validation

**Purpose**: Data validation, comparison, and quality checks.

### Functionality
- Trail balance validation
- Balance sheet validation
- Data comparison (imported vs calculated)
- Account validation
- Data quality checks
- Validation reporting

### Models
**⚠️ Status: Not yet implemented in v3**
These models exist in v2 (`apps/xero_validations/models.py`) but need to be migrated:
- `XeroTrailBalanceReport` - Stores imported trail balance reports from Xero API
- `XeroTrailBalanceReportLine` - Individual line items from trail balance reports
- `TrailBalanceComparison` - Comparison results between imported and calculated trail balances

### Views/Endpoints
**⚠️ Status: Not yet implemented in v3**
These views exist in v2 (`apps/xero_validations/views.py`) but have not yet been migrated to v3's `xero_validation` app. They should be implemented here:
- `ImportTrailBalanceView` - Import trail balance for comparison
- `CompareTrailBalanceView` - Compare imported vs calculated trail balance
- `ValidateBalanceSheetAccountsView` - Validate balance sheet accounts
- `ExportLineItemsView` - Export validation line items
- `AddIncomeStatementToReportView` - Add income statement to reports
- `TrailBalanceComparisonDetailsView` - Get detailed comparison results
- `ImportAndExportTrailBalanceView` - Combined import and export (testing)

### Services
**⚠️ Status: Not yet implemented in v3**
These services exist in v2 (`apps/xero_validations/services.py`) but need to be migrated:
- `import_trail_balance_from_xero` - Import trail balance from Xero API
- `compare_trail_balance` - Compare imported vs calculated trail balance
- `validate_balance_sheet_accounts` - Validate balance sheet accounts
- `export_all_line_items_to_csv` - Export validation results
- `add_income_statement_to_trail_balance_report` - Add income statement data
- `import_and_export_trail_balance` - Combined import and export (testing)

### Dependencies
- Depends on: `xero_core` (XeroTenant, XeroApiClient), `xero_cube` (for comparison data), `xero_metadata` (for account validation)
- Used by: Data quality checks, reporting validation

### Migration Status
⚠️ **Not yet migrated from v2**

The validation functionality exists in v2's `apps/xero_validations/` app but has **not yet been migrated** to v3's `xero_validation` app.

**Source location (v2):**
- Models: `apps/xero_validations/models.py` ✅ (exists)
- Views: `apps/xero_validations/views.py` ✅ (exists)
- Services: `apps/xero_validations/services.py` ✅ (exists)
- URLs: `apps/xero_validations/urls.py` ✅ (exists)

**Target location (v3):**
- Models: `apps/xero/xero_validation/models.py` ❌ (empty - needs migration)
- Views: `apps/xero/xero_validation/views.py` ❌ (empty - needs migration)
- Services: `apps/xero/xero_validation/services.py` ❌ (empty - needs migration)
- URLs: `apps/xero/xero_validation/urls.py` ❌ (empty - needs migration)

---

## Data Flow

```
User Authentication (xero_auth)
    ↓
Tenant Selection (xero_core)
    ↓
API Communication (xero_core - XeroApiClient)
    ↓
Data Sync (xero_sync) → Updates Metadata (xero_metadata) → Updates Data (xero_data)
    ↓
Data Processing (xero_cube) → Creates Trail Balance → Creates Balance Sheet
    ↓
Validation (xero_validation) → Validates Results
    ↓
External Integration (xero_integration) → Exports to BigQuery/External Systems
```

## Migration Strategy

### Step 1: Core Models
1. Move `XeroTenant` to `xero_core`
2. Update all foreign key references

### Step 2: Authentication
1. Move `XeroClientCredentials`, `XeroTenantToken`, `XeroAuthSettings` to `xero_auth`
2. Move auth views and OAuth logic to `xero_auth`

### Step 3: Metadata
1. Move `XeroBusinessUnits`, `XeroAccount`, `XeroTracking`, `XeroContacts` to `xero_metadata`
2. Move custom managers to `xero_metadata/managers.py`

### Step 4: Data Models
1. Move `XeroTransactionSource`, `XeroJournalsSource`, `XeroJournals` to `xero_data`
2. Move journal processing logic to `xero_data/services.py`

### Step 5: Sync
1. Move `XeroLastUpdate` to `xero_sync`
2. Move `XeroTenantSchedule` to `xero_sync` (scheduling is part of sync)
3. Move `XeroTaskExecutionLog` to `xero_sync` (task execution is part of sync)
4. Move `update_xero_models()` function to `xero_sync/services.py`
5. Move schedule management and task execution services to `xero_sync/services.py`

### Step 6: Cube
1. Move `XeroTrailBalance`, `XeroBalanceSheet` to `xero_cube`
2. Move consolidation logic (`create_trail_balance`, `create_balance_sheet`, `process_xero_data`) to `xero_cube/services.py`

### Step 7: Core API Clients
1. Move `XeroApiClient`, `XeroAccountingApi` to `xero_core/services.py`
2. Update all imports to use `xero_core` for API clients

### Step 8: Integration
1. Move BigQuery export functions to `xero_integration/services.py`
2. Move `export_accounts()` to `xero_integration/services.py` (if it's for external export)
3. Set up external integration services

### Step 9: Validation
1. Move validation views and logic to `xero_validation`
2. Move comparison services to `xero_validation/services.py`

## Import Patterns

After migration, imports will follow this pattern:

```python
# Core tenant and API clients
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_core.services import XeroApiClient, XeroAccountingApi

# Authentication
from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken
from apps.xero.xero_auth.services import refresh_token

# Metadata
from apps.xero.xero_metadata.models import XeroAccount, XeroContacts, XeroTracking

# Data
from apps.xero.xero_data.models import XeroJournals, XeroTransactionSource

# Sync (includes scheduling and task execution)
from apps.xero.xero_sync.models import XeroLastUpdate, XeroTenantSchedule, XeroTaskExecutionLog
from apps.xero.xero_sync.services import update_xero_models

# Cube
from apps.xero.xero_cube.models import XeroTrailBalance, XeroBalanceSheet
from apps.xero.xero_cube.services import create_trail_balance, process_xero_data

# Integration (external systems - BigQuery, data warehouses, etc.)
from apps.xero.xero_integration.services import export_to_bigquery, export_accounts

# Validation
from apps.xero.xero_validation.services import validate_trail_balance
```

## Benefits of This Architecture

1. **Separation of Concerns** - Each app has a single, well-defined responsibility
2. **Maintainability** - Easier to locate and modify specific functionality
3. **Testability** - Each app can be tested independently
4. **Scalability** - Apps can be scaled or optimized independently
5. **Reusability** - Services can be imported and reused across apps
6. **Clarity** - Clear boundaries make the codebase easier to understand
7. **Team Collaboration** - Different developers can work on different apps without conflicts

## Notes

- `XeroTenant` is the central model that all other apps reference
- `xero_core` contains the core tenant model AND the Xero API clients (`XeroApiClient`, `XeroAccountingApi`) - these are the foundation for all Xero API communication
- `xero_sync` handles everything related to triggering sync operations - scheduling, task execution, and data synchronization
- `xero_integration` is for external integrations and data distribution (BigQuery, data warehouses, third-party systems) - NOT for Xero API clients
- Foreign key relationships will need to be updated during migration
- Some services may need to be split across multiple apps (e.g., `process_xero_data` orchestrates multiple apps)
- Consider creating a `xero_common` app for shared utilities if needed
- All apps should follow Django best practices for models, managers, and services

