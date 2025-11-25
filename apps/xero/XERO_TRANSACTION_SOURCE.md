# XeroTransactionSource Update Locations

## Overview

`XeroTransactionSource` is updated in several locations throughout the codebase. This document tracks where transactions are created and updated.

## Update Locations

### 1. Model Manager Methods (`apps/xero/xero_data/models.py`)

The `XeroTransactionSourceModelManager` provides bulk operations for creating and updating transaction sources:

#### `_create_transactions_from_xero()`
- **Location**: `apps/xero/xero_data/models.py:14-67`
- **Purpose**: Helper method that handles bulk creation and updates
- **Updates**: 
  - Creates new `XeroTransactionSource` records
  - Updates existing records with new `contact`, `transaction_source`, and `collection` data
- **Bulk Operations**: Uses `bulk_create()` and `bulk_update()` for performance

#### `create_bank_transaction_from_xero()`
- **Location**: `apps/xero/xero_data/models.py:69-72`
- **Purpose**: Creates/updates bank transactions from Xero API response
- **Calls**: `_create_transactions_from_xero()` with `'BankTransaction'` type

#### `create_invoices_from_xero()`
- **Location**: `apps/xero/xero_data/models.py:74-77`
- **Purpose**: Creates/updates invoices from Xero API response
- **Calls**: `_create_transactions_from_xero()` with `'Invoice'` type

#### `create_payments_from_xero()`
- **Location**: `apps/xero/xero_data/models.py:79-82`
- **Purpose**: Creates/updates payments from Xero API response
- **Calls**: `_create_transactions_from_xero()` with `'Payment'` type

### 2. Service Layer (`apps/xero/xero_core/services.py`)

The `XeroTenant` model's service methods call the manager methods:

#### Bank Transactions
- **Location**: `apps/xero/xero_core/services.py:384`
- **Method**: `XeroTransactionSource.objects.create_bank_transaction_from_xero()`
- **Called from**: `XeroTenant` service methods when syncing bank transactions

#### Invoices
- **Location**: `apps/xero/xero_core/services.py:401`
- **Method**: `XeroTransactionSource.objects.create_invoices_from_xero()`
- **Called from**: `XeroTenant` service methods when syncing invoices

#### Payments
- **Location**: `apps/xero/xero_core/services.py:418`
- **Method**: `XeroTransactionSource.objects.create_payments_from_xero()`
- **Called from**: `XeroTenant` service methods when syncing payments

### 3. Update Process

The update process follows this pattern:

1. **Fetch from Xero API**: Get transaction data from Xero
2. **Pre-fetch Contacts**: Load all contacts into a dictionary for O(1) lookup
3. **Collect Transaction IDs**: Extract all transaction IDs from the response
4. **Fetch Existing**: Query existing transactions in one database query
5. **Compare & Categorize**: 
   - If transaction exists: Add to `to_update` list
   - If transaction is new: Add to `to_create` list
6. **Bulk Operations**: 
   - `bulk_create()` for new transactions
   - `bulk_update()` for existing transactions (updates: `contact`, `transaction_source`, `collection`)

### 4. Fields Updated

When updating existing transactions, these fields are modified:
- `contact`: ForeignKey to `XeroContacts`
- `transaction_source`: CharField (e.g., 'BankTransaction', 'Invoice', 'Payment')
- `collection`: JSONField containing the full Xero API response

### 5. Performance Optimizations

- **Bulk Operations**: Uses `bulk_create()` and `bulk_update()` instead of individual saves
- **Pre-fetching**: Contacts are pre-fetched into a dictionary for O(1) lookup
- **Single Query**: Existing transactions are fetched in one query using `__in` filter
- **Ignore Conflicts**: `bulk_create()` uses `ignore_conflicts=True` to handle race conditions

## Example Usage

```python
from apps.xero.xero_data.models import XeroTransactionSource
from apps.xero.xero_core.models import XeroTenant

# Get organisation
organisation = XeroTenant.objects.get(tenant_id='...')

# Fetch data from Xero API (example)
xero_response = [...]  # List of transaction dictionaries

# Create/update bank transactions
XeroTransactionSource.objects.create_bank_transaction_from_xero(
    organisation, 
    xero_response
)

# Create/update invoices
XeroTransactionSource.objects.create_invoices_from_xero(
    organisation,
    xero_response
)

# Create/update payments
XeroTransactionSource.objects.create_payments_from_xero(
    organisation,
    xero_response
)
```

## Related Models

- `XeroJournals`: References `XeroTransactionSource` via ForeignKey
- `XeroContacts`: Referenced by `XeroTransactionSource` via ForeignKey
- `XeroTenant`: Referenced by `XeroTransactionSource` via ForeignKey

