# Test Fixes Applied

## Issues Fixed

### 1. Missing `time` import in `xero_cube/services.py`
**Fixed:** Added `import time` to the imports

### 2. Scope field NULL constraint violations
**Fixed:** Added `scope=['accounting.transactions']` to all `XeroClientCredentials.objects.create()` calls in tests:
- `apps/xero/xero_core/tests.py`
- `apps/xero/xero_sync/tests.py` 
- `apps/xero/xero_sync/test_services.py`
- `apps/xero/xero_cube/tests.py`
- `apps/xero/xero_cube/test_services.py`
- `apps/xero/xero_auth/tests.py` (already had it)
- `apps/xero/test_views.py` (v2)
- `apps/xero/test_services.py` (v2)

### 3. Wrong field name: `process_interval_minutes`
**Fixed:** Removed `process_interval_minutes` from `XeroTenantSchedule.objects.create()` in `apps/xero/xero_sync/tests.py` - the model only has `update_interval_minutes`

### 4. Missing credentials in API client tests
**Fixed:** Added credential creation before initializing `XeroApiClient` in:
- `apps/xero/test_services.py` (v2)
- `apps/xero/xero_sync/test_services.py` (v3)

### 5. Missing credentials in sync view tests
**Fixed:** Added credentials to `setUp()` in `apps/xero/xero_sync/tests.py` for tests that need them

## Summary

All test files have been updated to:
- Provide `scope` field when creating credentials
- Use correct field names for `XeroTenantSchedule`
- Create credentials before initializing API clients
- Import missing `time` module

Tests should now run successfully inline!

