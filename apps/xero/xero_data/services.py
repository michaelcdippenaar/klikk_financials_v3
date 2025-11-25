"""
Service layer for xero_data-related business logic.
Handles updating transaction data (bank_transactions, invoices, payments, journals) from Xero API.
Note: All API calls are sequential to respect Xero's 5 concurrent call limit.
"""
import time
import logging

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_core.services import XeroApiClient, XeroAccountingApi
from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken

logger = logging.getLogger(__name__)


def update_xero_data(tenant_id, user=None, load_all=False, load_manual_journals=True, load_journals=True):
    """
    Service function to update Xero data models (transactions and journals) from API.
    This is separate from metadata updates (accounts, contacts, tracking).
    
    Args:
        tenant_id: Xero tenant ID
        user: User object (optional, will use first active credentials if not provided)
        load_all: If True (default), load both regular and manual journals. If False, check individual flags.
        load_manual_journals: If True (default), load manual journals. Only used if load_all=False.
        load_journals: If True (default), load regular journals. Only used if load_all=False.
    
    Returns:
        dict: Result with status, message, errors, and stats
    """
    start_time = time.time()
    
    try:
        tenant = XeroTenant.objects.get(tenant_id=tenant_id)
    except XeroTenant.DoesNotExist:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    # Find credentials that have a token for this tenant
    # Prefer credentials for the provided user, otherwise find any credentials with token for this tenant
    credentials = None
    if user:
        # Try to find credentials for the provided user that have a token for this tenant
        user_credentials = XeroClientCredentials.objects.filter(user=user, active=True)
        for cred in user_credentials:
            if cred.get_tenant_token_data(tenant_id):
                credentials = cred
                break
    
    # If not found, try to find any active credentials that have a token for this tenant
    if not credentials:
        all_credentials = XeroClientCredentials.objects.filter(active=True)
        for cred in all_credentials:
            if cred.get_tenant_token_data(tenant_id):
                credentials = cred
                break
    
    # If still not found, check XeroTenantToken model for backward compatibility
    if not credentials:
        try:
            tenant = XeroTenant.objects.get(tenant_id=tenant_id)
            tenant_token = XeroTenantToken.objects.filter(tenant=tenant, credentials__active=True).first()
            if tenant_token:
                credentials = tenant_token.credentials
        except XeroTenant.DoesNotExist:
            pass
    
    if not credentials:
        raise ValueError(f"No active credentials found with token for tenant {tenant_id}. Please re-authenticate this tenant.")
    
    user = credentials.user
    
    stats = {
        'bank_transactions_updated': 0,
        'invoices_updated': 0,
        'payments_updated': 0,
        'journals_updated': 0,
        'manual_journals_updated': 0,
        'api_calls': 0,
    }
    
    errors = []
    
    try:
        api_client = XeroApiClient(user, tenant_id=tenant_id)
        xero_api = XeroAccountingApi(api_client, tenant_id)
        stats['api_calls'] += 1  # Initial API client creation

        # Transaction-related calls (executed sequentially to respect Xero's 5 concurrent call limit)
        # transaction_calls = [
        #     ('bank_transactions', lambda: xero_api.bank_transactions().get()),
        #     ('invoices', lambda: xero_api.invoices().get()),
        #     ('payments', lambda: xero_api.payments().get()),
        # ]
        
        # Execute transaction calls sequentially
        # print(f"[DATA UPDATE] Starting transaction updates: bank_transactions, invoices, payments")
        # stats['api_calls'] += len(transaction_calls)  # Count API calls
        # for name, call in transaction_calls:
        #     try:
        #         call()
        #         stats[f'{name}_updated'] = 1
        #         print(f"[DATA UPDATE] ✓ {name} finished")
        #         logger.info(f"Successfully updated {name} for tenant {tenant_id}")
        #     except Exception as e:
        #         error_msg = f"Failed to update {name}: {str(e)}"
        #         print(f"[DATA UPDATE] ✗ {name} failed: {str(e)}")
        #         logger.error(error_msg)
        #         errors.append(error_msg)
        # print(f"[DATA UPDATE] Transaction updates completed")
        
        # Journals should run last (may depend on other data)
        # Use the unified load_journals method with parameters
        # load_all controls timestamp behavior (ignore vs incremental), not which types to load
        if load_journals or load_manual_journals:
            journal_types = []
            if load_journals:
                journal_types.append('regular')
            if load_manual_journals:
                journal_types.append('manual')
            print(f"[DATA UPDATE] Starting journals update ({', '.join(journal_types)})")
            
            # Use the unified load_journals method
            # load_all=True means ignore timestamp and load everything for selected types
            journal_results = xero_api.load_journals(
                load_all=load_all,
                load_manual_journals=load_manual_journals,
                load_journals=load_journals
            )
            
            # Update stats based on what was loaded
            for journal_type in journal_results['loaded_types']:
                stats[f'{journal_type}_updated'] = 1
                print(f"[DATA UPDATE] ✓ {journal_type} finished")
                logger.info(f"Successfully updated {journal_type} for tenant {tenant_id}")
            
            # Add any errors from journal loading
            if journal_results['errors']:
                errors.extend(journal_results['errors'])
                for error in journal_results['errors']:
                    print(f"[DATA UPDATE] ✗ {error}")
                    logger.error(error)
            
            # Count API calls (estimate: 1 per journal type loaded)
            stats['api_calls'] += len(journal_results['loaded_types'])
        else:
            print(f"[DATA UPDATE] Skipping journals update (no journal types selected)")
        
        duration = time.time() - start_time
        stats['duration_seconds'] = duration
        stats['total_errors'] = len(errors)
        
        print(f"[DATA UPDATE] All data updates completed in {duration:.2f} seconds. Errors: {len(errors)}")
        
        messages = [f"Data updated for tenant {tenant_id}"]
        
        return {
            'success': len(errors) == 0,
            'message': '. '.join(messages),
            'errors': errors,
            'stats': stats
        }
        
    except ValueError as e:
        # Handle authentication/token errors specifically
        duration = time.time() - start_time
        error_msg = f"Authentication error for tenant {tenant_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Re-raise as ValueError to distinguish from other exceptions
        raise ValueError(error_msg) from e
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Failed to update data for tenant {tenant_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
