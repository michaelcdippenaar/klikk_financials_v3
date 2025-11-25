"""
Xero cube services - data processing and consolidation.
"""
import datetime
import time
import logging
import pandas as pd
from decimal import Decimal
from django.db.models import Q, Sum, F

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_data.models import XeroJournals, Month, Year
from apps.xero.xero_cube.models import XeroTrailBalance, XeroBalanceSheet

logger = logging.getLogger(__name__)


def process_journals(tenant_id):
    """Process journals from source."""
    print('[PROCESS JOURNALS] Start Processing Journals from XeroJournalsSource')
    logger.info(f'Start Processing Journals for tenant {tenant_id}')
    organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    from apps.xero.xero_data.models import XeroJournalsSource
    result = XeroJournalsSource.objects.create_journals_from_xero(organisation)
    print(f'[PROCESS JOURNALS] Journals processing complete')
    logger.info(f'Journals processing complete for tenant {tenant_id}')


def create_trail_balance(tenant_id, incremental=False, rebuild=False, exclude_manual_journals=False):
    """
    Create trail balance from journals.
    
    Args:
        tenant_id: Xero tenant ID
        incremental: If True, only process journals updated since last run
        rebuild: If True, force full rebuild and ignore existing data (overrides incremental)
        exclude_manual_journals: If True, only build trail balance from regular journals (exclude manual journals)
    """
    from apps.xero.xero_sync.models import XeroLastUpdate
    
    organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    
    # If rebuild is True, force full rebuild regardless of incremental setting
    if rebuild:
        logger.info("Rebuild mode: forcing full rebuild and ignoring existing data")
        print(f"[TRAIL BALANCE] REBUILD mode: forcing full rebuild, ignoring existing data")
        if exclude_manual_journals:
            print(f"[TRAIL BALANCE] REBUILD mode: excluding manual journals - only using regular journals")
        incremental = False
        last_update_date = None
    # Get last update date for incremental updates
    elif incremental:
        try:
            last_update = XeroLastUpdate.objects.get(
                end_point='journals',
                organisation=organisation
            )
            if last_update.date:
                last_update_date = last_update.date
                logger.info(f"Using incremental update from {last_update_date}")
                print(f"[TRAIL BALANCE] Using incremental update from {last_update_date}")
        except XeroLastUpdate.DoesNotExist:
            logger.info("No previous update found, doing full rebuild")
            print(f"[TRAIL BALANCE] No previous update found, doing full rebuild")
    
    # Get account balances - filter by date if incremental
    if last_update_date:
        # For incremental updates, we need to:
        # 1. First, get the affected periods (year/month) from new journals
        # 2. Then get ALL journals for those periods (not just new ones) to recalculate totals correctly
        logger.info(f"Incremental update mode: identifying affected periods since {last_update_date}")
        print(f"[TRAIL BALANCE] Incremental update mode: identifying affected periods since {last_update_date}")
        
        # Step 1: Get new journals to identify affected periods
        new_journals_filter = XeroJournals.objects.filter(
            organisation=organisation,
            date__gte=last_update_date
        )
        # Exclude manual journals if requested
        if exclude_manual_journals:
            new_journals_filter = new_journals_filter.exclude(journal_type='manual_journal')
        
        new_journals = new_journals_filter.annotate(
            month=Month('date'),
            year=Year('date')
        ).values('year', 'month').distinct()
        
        affected_periods = list(new_journals)
        logger.info(f"Affected periods: {affected_periods}")
        print(f"[TRAIL BALANCE] Found {len(affected_periods)} affected periods: {affected_periods}")
        
        if affected_periods:
            # Step 2: Get ALL journals for affected periods (not just new ones)
            # This ensures we recalculate totals correctly
            period_filters = Q()
            for period in affected_periods:
                period_filters |= Q(
                    date__year=period['year'],
                    date__month=period['month']
                )
            
            # Get all journals for affected periods
            qs = XeroJournals.objects.filter(
                organisation=organisation
            ).filter(period_filters)
            # Exclude manual journals if requested
            if exclude_manual_journals:
                qs = qs.exclude(journal_type='manual_journal')
            
            qs = qs.annotate(
                month=Month('date')
            ).annotate(
                year=Year('date')
            ).annotate(
                contact=F('transaction_source__contact')
            ).values("account", "year", "month", "contact", "tracking1", "tracking2").order_by().annotate(
                amount=Sum("amount"),
            )
            logger.info(f"Incremental update: recalculating {len(affected_periods)} affected periods with all journals")
            print(f"[TRAIL BALANCE] Recalculating {len(affected_periods)} affected periods, found {qs.count()} journal aggregates")
        else:
            logger.warning("No affected periods found in incremental mode, but continuing with full rebuild")
            print(f"[TRAIL BALANCE] WARNING: No affected periods found, falling back to full rebuild")
            # Fall back to full rebuild if no affected periods
            qs = XeroJournals.objects.get_account_balances(organisation, exclude_manual_journals=exclude_manual_journals)
            last_update_date = None  # Clear last_update_date to trigger full rebuild in consolidate_journals
    else:
        # Get all balances for full rebuild
        logger.info("Full rebuild mode: getting all account balances")
        print(f"[TRAIL BALANCE] Full rebuild mode: getting all account balances")
        if exclude_manual_journals:
            print(f"[TRAIL BALANCE] Excluding manual journals - only using regular journals")
        qs = XeroJournals.objects.get_account_balances(organisation, exclude_manual_journals=exclude_manual_journals)
        print(f"[TRAIL BALANCE] Found {qs.count()} journal aggregates for full rebuild")
    
    print(f'[TRAIL BALANCE] Start Consolidate Journal Process - {qs.count()} journal aggregates to process')
    logger.info(f"Consolidating {qs.count()} journal aggregates into trail balance")
    
    # Convert queryset to list to ensure we can iterate multiple times
    journals_list = list(qs)
    print(f'[TRAIL BALANCE] Converted to list: {len(journals_list)} items')
    
    # Track Trail Balance creation
    from apps.xero.xero_sync.models import XeroLastUpdate
    
    try:
        result = XeroTrailBalance.objects.consolidate_journals(organisation, journals_list, last_update_date=last_update_date)
        print(f'[TRAIL BALANCE] Consolidation complete, checking created records...')
        
        tb = XeroTrailBalance.objects.filter(organisation=organisation).select_related(
            'account', 'account__business_unit', 'contact', 'tracking1', 'tracking2', 'organisation'
        )
        tb_count = tb.count()
        
        # Check for errors - if consolidation returned empty or count is 0, don't update timestamp
        if tb_count == 0:
            error_msg = "Trail Balance creation resulted in 0 records"
            logger.error(error_msg)
            print(f'[TRAIL BALANCE] ERROR: {error_msg}')
            # Don't update timestamp on error - preserve last successful date
        else:
            # Success - update timestamp
            XeroLastUpdate.objects.update_or_create_timestamp('trail_balance', organisation)
            print(f'[TRAIL BALANCE] Successfully created {tb_count} records')
    except Exception as e:
        error_msg = f"Trail Balance creation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f'[TRAIL BALANCE] ERROR: {error_msg}')
        # Don't update timestamp on error - preserve last successful date
        raise
    print(f'[TRAIL BALANCE] Total trail balance records after consolidation: {tb_count}')
    logger.info(f"Trail balance consolidation complete: {tb_count} total records")
    
    print('Start Trail Balance - Google Export')
    
    df = tb.to_dataframe([
        'organisation__tenant_id', 'organisation__tenant_name',
        'year', 'month', 'fin_year', 'fin_period',
        'account__account_id',
        'account__type',
        'account__grouping',
        'account__code',
        'account__name',
        'account__business_unit__business_unit_code',
        'account__business_unit__business_unit_description',
        'account__business_unit__division_code',
        'account__business_unit__division_description',
        'contact__name',
        'contact__contacts_id',
        'tracking1__option',
        'tracking2__option',
        'amount',
        'balance_to_date'
    ])

    print('Trail Balance - DataFrame Created')

    # Filter zero amounts and convert to numeric types for BigQuery
    df = df[df.amount != 0].copy()
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['fin_period'] = pd.to_numeric(df['fin_period'], errors='coerce')
    # Convert balance_to_date to numeric (may be NaN for non-P&L accounts)
    df['balance_to_date'] = pd.to_numeric(df['balance_to_date'], errors='coerce')
    table_id = f'Xero.TrailBalance_Movement_V2_{tenant_id.replace("-", "_")}'
    
    # Export to BigQuery (via integration service)
    from apps.xero.xero_integration.services import update_google_big_query, run_async_export, update_google_big_query_async
    try:
        run_async_export(update_google_big_query_async(df, table_id))
    except Exception as e:
        # Fallback to sync version if async fails
        logger.warning(f"Async export failed, using sync: {str(e)}")
        update_google_big_query(df, table_id)
    print('End Trail Balance - Google Export')


def calculate_profit_loss_balance_to_date(tenant_id):
    """
    Calculate balance_to_date (YTD) for Profit & Loss accounts.
    
    For P&L accounts (REVENUE and EXPENSE), calculates the cumulative sum
    of all previous months up to and including the current month.
    This is done after processing the cube.
    
    Args:
        tenant_id: Xero tenant ID
    """
    from apps.xero.xero_cube.models import XeroTrailBalance
    
    logger.info(f'Start calculating P&L balance_to_date for tenant {tenant_id}')
    print(f"[P&L YTD] Starting balance_to_date calculation for tenant {tenant_id}")
    
    try:
        organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    except XeroTenant.DoesNotExist:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    # P&L account types
    pnl_account_types = ['REVENUE', 'EXPENSE']
    
    # Get all P&L accounts for this organisation
    pnl_accounts = XeroTrailBalance.objects.filter(
        organisation=organisation,
        account__type__in=pnl_account_types
    ).select_related('account', 'contact', 'tracking1', 'tracking2').order_by(
        'account', 'contact', 'tracking1', 'tracking2', 'year', 'month'
    )
    
    if not pnl_accounts.exists():
        logger.info(f"No P&L accounts found for tenant {tenant_id}")
        print(f"[P&L YTD] No P&L accounts found")
        return
    
    # Group by account, contact, tracking1, tracking2 to calculate YTD for each combination
    # Balance to date = total of all previous months (cumulative from the start)
    # Get distinct combinations
    distinct_combinations = pnl_accounts.values(
        'account', 'contact', 'tracking1', 'tracking2'
    ).distinct()
    
    total_updated = 0
    batch_size = 1000
    to_update = []
    
    print(f"[P&L YTD] Processing {distinct_combinations.count()} account/contact/tracking combinations")
    logger.info(f"Processing {distinct_combinations.count()} account/contact/tracking combinations")
    
    for combo in distinct_combinations:
        # Get all records for this combination, ordered by year and month
        # This ensures we calculate cumulative balance correctly across all periods
        records = pnl_accounts.filter(
            account=combo['account'],
            contact=combo['contact'],
            tracking1=combo['tracking1'],
            tracking2=combo['tracking2']
        ).order_by('year', 'month')
        
        # Calculate cumulative balance (balance_to_date) for each record
        # Balance to date = sum of all previous months up to and including current month
        cumulative_balance = Decimal('0')
        
        for record in records:
            # Add current month's amount to cumulative balance
            cumulative_balance += record.amount
            
            # Update balance_to_date if it's different
            if record.balance_to_date != cumulative_balance:
                record.balance_to_date = cumulative_balance
                to_update.append(record)
                
                # Batch update when we reach batch_size
                if len(to_update) >= batch_size:
                    XeroTrailBalance.objects.bulk_update(
                        to_update,
                        ['balance_to_date'],
                        batch_size=batch_size
                    )
                    total_updated += len(to_update)
                    print(f"[P&L YTD] Updated {total_updated} records...")
                    to_update = []
    
    # Update remaining records
    if to_update:
        XeroTrailBalance.objects.bulk_update(
            to_update,
            ['balance_to_date'],
            batch_size=batch_size
        )
        total_updated += len(to_update)
    
    logger.info(f"Completed balance_to_date calculation: updated {total_updated} P&L records")
    print(f"[P&L YTD] ✓ Completed: updated {total_updated} P&L records")


def create_balance_sheet(tenant_id):
    """Create balance sheet from trail balance."""
    organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    XeroBalanceSheet.objects.consolidate_balance_sheet(organisation)
    tb = XeroBalanceSheet.objects.filter(organisation=organisation).select_related(
        'account', 'account__business_unit', 'contact', 'organisation'
    )
    df = tb.to_dataframe([
        'organisation__tenant_id', 'organisation__tenant_name', 'year', 'month',
        'account__account_id', 'account__type', 'account__business_unit__division_code',
        'account__business_unit__division_description', 'account__business_unit__business_unit_code',
        'account__business_unit__business_unit_description', 'account__grouping', 'account__code',
        'account__name', 'contact__name', 'amount', 'balance'
    ])
    df['amount'] = pd.to_numeric(df['amount'])
    df['balance'] = pd.to_numeric(df['balance'])
    table_id = f'Xero.BalanceSheet_Balance_{tenant_id.replace("-", "_")}'
    
    # Export to BigQuery (via integration service)
    from apps.xero.xero_integration.services import update_google_big_query, run_async_export, update_google_big_query_async
    try:
        run_async_export(update_google_big_query_async(df, table_id))
    except Exception as e:
        # Fallback to sync version if async fails
        logger.warning(f"Async export failed, using sync: {str(e)}")
        update_google_big_query(df, table_id)


def process_xero_data(tenant_id, rebuild_trail_balance=False, exclude_manual_journals=False):
    """
    Service function to process Xero data (trail balance, etc.).
    Extracted from XeroProcessDataView for use in scheduled tasks.
    
    Processing order:
    1. Process journals from XeroJournalsSource to XeroJournals
    2. Create trail balance from processed journals
    3. Calculate balance_to_date for P&L accounts
    
    Note: Metadata and Data Source updates must complete before this runs.
    
    Args:
        tenant_id: Xero tenant ID
        rebuild_trail_balance: If True, force full rebuild of trail balance and ignore existing data
        exclude_manual_journals: If True, only build trail balance from regular journals (exclude manual journals)
    
    Returns:
        dict: Result with status, message, and stats
    """
    start_time = time.time()
    
    try:
        tenant = XeroTenant.objects.get(tenant_id=tenant_id)
    except XeroTenant.DoesNotExist:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    stats = {
        'journals_processed': False,
        'trail_balance_created': False,
        'pnl_balance_to_date_calculated': False,
        'balance_sheet_created': False,
        'accounts_exported': False,
    }
    
    try:
        # Step 1: Process journals from XeroJournalsSource to XeroJournals
        logger.info(f'Start Processing Journals for tenant {tenant_id}')
        print(f"[PROCESS] Starting journal processing for tenant {tenant_id}")
        process_journals(tenant_id)
        stats['journals_processed'] = True
        print(f"[PROCESS] ✓ Journals processed")
        logger.info(f'Journals processed for tenant {tenant_id}')
        
        # Step 2: Create trail balance from processed journals
        logger.info(f'Start Creating Trail Balance for tenant {tenant_id}')
        print(f"[PROCESS] Starting trail balance creation for tenant {tenant_id}")
        if rebuild_trail_balance:
            print(f"[PROCESS] REBUILD mode: forcing full rebuild of trail balance")
        if exclude_manual_journals:
            print(f"[PROCESS] Excluding manual journals - only using regular journals for trail balance")
        create_trail_balance(tenant_id, incremental=not rebuild_trail_balance, rebuild=rebuild_trail_balance, exclude_manual_journals=exclude_manual_journals)
        stats['trail_balance_created'] = True
        print(f"[PROCESS] ✓ Trail balance created")
        
        # Step 3: Calculate balance_to_date for P&L accounts
        logger.info(f'Start calculating P&L balance_to_date for tenant {tenant_id}')
        print(f"[PROCESS] Starting P&L balance_to_date calculation for tenant {tenant_id}")
        calculate_profit_loss_balance_to_date(tenant_id)
        stats['pnl_balance_to_date_calculated'] = True
        print(f"[PROCESS] ✓ P&L balance_to_date calculated")
        
        # Uncomment if needed
        # create_balance_sheet(tenant_id)
        # stats['balance_sheet_created'] = True
        
        # Uncomment if needed
        # from apps.xero.xero_integration.services import export_accounts
        # export_accounts(tenant_id)
        # stats['accounts_exported'] = True
        
        duration = time.time() - start_time
        stats['duration_seconds'] = duration
        
        return {
            'success': True,
            'message': f"Data processed for tenant {tenant_id}",
            'stats': stats
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Failed to process data for tenant {tenant_id}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def process_profit_loss(tenant_id, user=None):
    """
    Process Profit & Loss reports - import and validate.
    
    This runs after process_xero_data completes.
    
    Args:
        tenant_id: Xero tenant ID
        user: User object for API authentication (optional)
    
    Returns:
        dict: Result with status, message, and stats
    """
    from apps.xero.xero_validation.services.imports import import_profit_loss_from_xero
    from apps.xero.xero_validation.services.profit_loss_validation import validate_profit_loss_with_fallback
    from apps.xero.xero_sync.models import XeroLastUpdate
    from datetime import date, timedelta
    
    start_time = time.time()
    organisation = XeroTenant.objects.get(tenant_id=tenant_id)
    
    stats = {
        'pnl_imported': False,
        'pnl_validated': False,
        'in_sync': True,
    }
    
    try:
        # Calculate date range for P&L report (last 12 months)
        to_date = date.today()
        from_date = to_date - timedelta(days=365)  # Approximately 12 months
        
        # Import P&L report
        logger.info(f'Starting P&L import for tenant {tenant_id}')
        print(f"[P&L] Starting P&L import for tenant {tenant_id}")
        import_result = import_profit_loss_from_xero(
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date,
            periods=11,  # 12 months (0-11)
            timeframe='MONTH',
            user=user
        )
        
        if import_result.get('success'):
            stats['pnl_imported'] = True
            print(f"[P&L] ✓ P&L imported successfully")
            logger.info(f'P&L imported for tenant {tenant_id}')
            # Update timestamp immediately after API call succeeds, before validation
            XeroLastUpdate.objects.update_or_create_timestamp('profit_loss', organisation)
        else:
            raise Exception(f"P&L import failed: {import_result.get('message', 'Unknown error')}")
        
        # Validate P&L (with fallback to previous month)
        logger.info(f'Starting P&L validation for tenant {tenant_id}')
        print(f"[P&L] Starting P&L validation for tenant {tenant_id}")
        validation_result = validate_profit_loss_with_fallback(tenant_id)
        
        stats['pnl_validated'] = True
        stats['in_sync'] = validation_result.get('in_sync', False)
        stats['validation_errors'] = len(validation_result.get('errors', []))
        
        if validation_result.get('in_sync'):
            print(f"[P&L] ✓ P&L validation passed")
            logger.info(f'P&L validation passed for tenant {tenant_id}')
        else:
            print(f"[P&L] ✗ P&L validation failed: {len(validation_result.get('errors', []))} errors")
            logger.warning(f'P&L validation failed for tenant {tenant_id}: {validation_result.get("errors", [])[:3]}')
            # Don't update timestamp on validation failure - preserve last successful date
        
        duration = time.time() - start_time
        stats['duration_seconds'] = duration
        
        return {
            'success': True,
            'message': f"P&L processed for tenant {tenant_id}",
            'stats': stats,
            'validation_result': validation_result
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Failed to process P&L for tenant {tenant_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Don't update timestamp on error - preserve last successful date
        
        stats['duration_seconds'] = duration
        return {
            'success': False,
            'message': error_msg,
            'stats': stats
        }
