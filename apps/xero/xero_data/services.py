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


def update_xero_data(tenant_id, user=None, load_all=False):
    """
    Service function to update Xero data models (transactions and journals) from API.
    This is separate from metadata updates (accounts, contacts, tracking).
    
    Args:
        tenant_id: Xero tenant ID
        user: User object (optional, will use first active credentials if not provided)
        load_all: If True, ignore last update timestamp and load all journals. If False (default), use incremental updates.
    
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
        # Call journals method directly
        print(f"[DATA UPDATE] Starting journals update (load_all={load_all})")
        try:
            xero_api.journals(load_all=load_all).get()
            stats['journals_updated'] = 1
            stats['api_calls'] += 1
            print(f"[DATA UPDATE] ✓ journals finished")
            logger.info(f"Successfully updated journals for tenant {tenant_id}")
        except Exception as e:
            error_msg = f"Failed to update journals: {str(e)}"
            print(f"[DATA UPDATE] ✗ journals failed: {str(e)}")
            logger.error(error_msg)
            errors.append(error_msg)
        
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
