# Testing Guide: v2 vs v3 Comparison

This document describes the unit test suite created to ensure that both v2 and v3 of the Xero application function identically.

## Test Structure

### v2 Tests (`klikk_financials_v2/klikk_business_intelligence/apps/xero/`)

- **`tests.py`** - Model tests (XeroTenantSchedule, XeroTaskExecutionLog, scheduler tests)
- **`test_views.py`** - View tests (authentication, tenant management, data sync, processing)
- **`test_services.py`** - Service tests (update_xero_models, process_xero_data, XeroApiClient)

### v3 Tests (`klikk_financials_v3/apps/xero/`)

Tests are organized by app:

- **`xero_auth/tests.py`** - Authentication view tests
- **`xero_core/tests.py`** - Tenant management and model tests
- **`xero_sync/tests.py`** - Sync views and model tests
- **`xero_sync/test_services.py`** - Sync service tests
- **`xero_cube/tests.py`** - Data processing and summary view tests
- **`xero_cube/test_services.py`** - Data processing service tests

## Test Coverage

### Models Tested

- ✅ `XeroTenant` - Tenant creation, uniqueness
- ✅ `XeroClientCredentials` - Credential management
- ✅ `XeroTenantToken` - Token storage
- ✅ `XeroTenantSchedule` - Schedule logic, should_run methods
- ✅ `XeroTaskExecutionLog` - Log creation, completion, failure tracking

### Views Tested

- ✅ `XeroAuthInitiateView` - OAuth initiation
- ✅ `XeroCallbackView` - OAuth callback handling
- ✅ `XeroTenantListView` - Tenant listing
- ✅ `XeroUpdateModelsView` - Data synchronization trigger
- ✅ `XeroProcessDataView` - Data processing trigger
- ✅ `XeroDataSummaryView` - Data summary retrieval

### Services Tested

- ✅ `update_xero_models` - Data synchronization service
- ✅ `process_xero_data` - Data processing service
- ✅ `XeroApiClient` - API client initialization

## Running Tests

### Run v2 Tests

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence
python manage.py test apps.xero
```

### Run v3 Tests

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python manage.py test apps.xero
```

### Run Specific Test Files

**v2:**
```bash
# Views only
python manage.py test apps.xero.test_views

# Services only
python manage.py test apps.xero.test_services

# Models only
python manage.py test apps.xero.tests
```

**v3:**
```bash
# Auth tests
python manage.py test apps.xero.xero_auth

# Core tests
python manage.py test apps.xero.xero_core

# Sync tests
python manage.py test apps.xero.xero_sync

# Cube tests
python manage.py test apps.xero.xero_cube
```

### Run Comparison Script

The comparison script runs tests in both versions and compares results:

```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python scripts/run_tests_comparison.py
```

## Test Equivalency

The following test cases are equivalent between v2 and v3:

| v2 Test | v3 Test | Description |
|---------|---------|-------------|
| `XeroAuthInitiateViewTest` | `xero_auth.tests.XeroAuthInitiateViewTest` | OAuth initiation |
| `XeroCallbackViewTest` | `xero_auth.tests.XeroCallbackViewTest` | OAuth callback |
| `XeroTenantListViewTest` | `xero_core.tests.XeroTenantListViewTest` | Tenant listing |
| `XeroUpdateModelsViewTest` | `xero_sync.tests.XeroUpdateModelsViewTest` | Data sync trigger |
| `XeroProcessDataViewTest` | `xero_cube.tests.XeroProcessDataViewTest` | Data processing |
| `XeroDataSummaryViewTest` | `xero_cube.tests.XeroDataSummaryViewTest` | Data summary |
| `UpdateXeroModelsServiceTest` | `xero_sync.test_services.UpdateXeroModelsServiceTest` | Sync service |
| `ProcessXeroDataServiceTest` | `xero_cube.test_services.ProcessXeroDataServiceTest` | Processing service |
| `XeroTenantScheduleModelTest` | `xero_sync.tests.XeroTenantScheduleModelTest` | Schedule model |
| `XeroTaskExecutionLogModelTest` | `xero_sync.tests.XeroTaskExecutionLogModelTest` | Log model |

## Expected Behavior

All tests should:
1. ✅ Pass in both v2 and v3
2. ✅ Produce identical results for equivalent functionality
3. ✅ Cover the same edge cases and error scenarios
4. ✅ Use the same mocking strategies

## Troubleshooting

### Import Errors

If you see import errors, ensure:
- All dependencies are installed (`pip install -r requirements.txt`)
- Django settings are configured correctly
- Virtual environment is activated

### Test Failures

If tests fail:
1. Check that database migrations are up to date
2. Verify that test fixtures are set up correctly
3. Ensure mock objects match the actual API structure
4. Check that URL patterns match between v2 and v3

### Mock Issues

The tests use extensive mocking to avoid external API calls. If mocks fail:
- Verify mock return values match expected API responses
- Check that mock patches target the correct import paths
- Ensure mock objects have all required attributes

## Adding New Tests

When adding new functionality:

1. **Add test to v2 first** - Write the test in the monolithic structure
2. **Add equivalent test to v3** - Adapt to the new app structure
3. **Ensure equivalence** - Both tests should test the same behavior
4. **Update this document** - Add the new test to the equivalency table

## Continuous Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Test v2
  run: |
    cd klikk_financials_v2/klikk_business_intelligence
    python manage.py test apps.xero

- name: Test v3
  run: |
    cd klikk_financials_v3
    python manage.py test apps.xero

- name: Compare Results
  run: |
    cd klikk_financials_v3
    python scripts/run_tests_comparison.py
```

## Notes

- Tests use `unittest.mock` to avoid external API dependencies
- APScheduler is mocked to prevent scheduler initialization during tests
- Database is isolated per test using Django's TestCase
- Authentication is handled via `APIClient.force_authenticate()`

