# Quick Test Guide - Run Tests Inline

## Test Files Created

### v2 Tests
- `apps/xero/test_views.py` - 19 view test cases
- `apps/xero/test_services.py` - 6 service test cases
- `apps/xero/tests.py` - 21 existing test cases (models, scheduler)

### v3 Tests
- `apps/xero/xero_auth/tests.py` - 7 auth test cases
- `apps/xero/xero_core/tests.py` - 5 core test cases
- `apps/xero/xero_sync/tests.py` - 10 sync test cases
- `apps/xero/xero_sync/test_services.py` - 4 service test cases
- `apps/xero/xero_cube/tests.py` - 5 cube test cases
- `apps/xero/xero_cube/test_services.py` - 2 service test cases

## Running Tests

### Option 1: Run All Tests

**v2:**
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence
python manage.py test apps.xero.test_views apps.xero.test_services apps.xero.tests
```

**v3:**
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python manage.py test apps.xero
```

### Option 2: Run Specific Test Classes

**v2 - View Tests:**
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence
python manage.py test apps.xero.test_views.XeroAuthInitiateViewTest
python manage.py test apps.xero.test_views.XeroCallbackViewTest
python manage.py test apps.xero.test_views.XeroTenantListViewTest
python manage.py test apps.xero.test_views.XeroUpdateModelsViewTest
python manage.py test apps.xero.test_views.XeroProcessDataViewTest
python manage.py test apps.xero.test_views.XeroDataSummaryViewTest
```

**v3 - Auth Tests:**
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python manage.py test apps.xero.xero_auth.tests.XeroAuthInitiateViewTest
python manage.py test apps.xero.xero_auth.tests.XeroCallbackViewTest
```

**v3 - Core Tests:**
```bash
python manage.py test apps.xero.xero_core.tests.XeroTenantListViewTest
python manage.py test apps.xero.xero_core.tests.XeroTenantModelTest
```

**v3 - Sync Tests:**
```bash
python manage.py test apps.xero.xero_sync.tests.XeroUpdateModelsViewTest
python manage.py test apps.xero.xero_sync.tests.XeroTenantScheduleModelTest
python manage.py test apps.xero.xero_sync.tests.XeroTaskExecutionLogModelTest
python manage.py test apps.xero.xero_sync.test_services.UpdateXeroModelsServiceTest
```

**v3 - Cube Tests:**
```bash
python manage.py test apps.xero.xero_cube.tests.XeroProcessDataViewTest
python manage.py test apps.xero.xero_cube.tests.XeroDataSummaryViewTest
python manage.py test apps.xero.xero_cube.test_services.ProcessXeroDataServiceTest
```

### Option 3: Run Individual Test Methods

**v2:**
```bash
python manage.py test apps.xero.test_views.XeroAuthInitiateViewTest.test_auth_initiate_success
python manage.py test apps.xero.test_views.XeroAuthInitiateViewTest.test_auth_initiate_no_credentials
```

**v3:**
```bash
python manage.py test apps.xero.xero_auth.tests.XeroAuthInitiateViewTest.test_auth_initiate_success
python manage.py test apps.xero.xero_auth.tests.XeroAuthInitiateViewTest.test_auth_initiate_no_credentials
```

### Option 4: Use Test Scripts

**Verify Syntax:**
```bash
cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v3
python scripts/verify_tests.py
```

**Run Comparison:**
```bash
python scripts/run_tests_comparison.py
```

**Run Inline:**
```bash
python scripts/run_tests_inline.py
```

## Expected Output

When tests pass, you should see:
```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
test_auth_initiate_success (apps.xero.test_views.XeroAuthInitiateViewTest) ... ok
test_auth_initiate_no_credentials (apps.xero.test_views.XeroAuthInitiateViewTest) ... ok
...

----------------------------------------------------------------------
Ran 19 tests in X.XXXs

OK
Destroying test database for alias 'default'...
```

## Troubleshooting

### Import Errors
- Ensure Django is installed: `pip install Django`
- Ensure REST framework is installed: `pip install djangorestframework`
- Check that virtual environment is activated

### Database Errors
- Tests use a separate test database automatically
- Ensure database settings are correct in `settings.py`

### Mock Errors
- Tests mock external dependencies (Xero API, APScheduler)
- If mocks fail, check that import paths match your code structure

## Test Coverage Summary

| Component | v2 Tests | v3 Tests |
|-----------|----------|----------|
| Authentication Views | 7 | 7 |
| Tenant Management | 3 | 5 |
| Data Sync Views | 4 | 4 |
| Data Processing Views | 5 | 5 |
| Sync Services | 3 | 3 |
| Processing Services | 2 | 2 |
| Schedule Models | 8 | 4 |
| Task Log Models | 3 | 2 |
| **Total** | **46** | **33** |

## Quick Verification

To quickly verify tests are set up correctly:

```bash
# Check syntax
python -m py_compile apps/xero/test_views.py

# List available tests
python manage.py test apps.xero.test_views --dry-run

# Run with verbose output
python manage.py test apps.xero.test_views --verbosity=2
```

