"""
Background service to check and retry out-of-sync data.
Runs at predetermined intervals to identify and fix sync issues.
"""
import logging
from datetime import timedelta
from django.utils import timezone

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_sync.models import XeroLastUpdate
from apps.xero.xero_sync.services import update_xero_models
from apps.xero.xero_cube.services import process_xero_data, process_profit_loss
from apps.xero.xero_validation.services.profit_loss_validation import validate_profit_loss_with_fallback

logger = logging.getLogger(__name__)


def check_and_retry_out_of_sync(tenant_id=None, max_retry_age_hours=24):
    """
    Check for out-of-sync endpoints and retry them.
    
    Args:
        tenant_id: Optional tenant ID to check. If None, checks all tenants.
        max_retry_age_hours: Only retry items that have been out of sync for less than this many hours.
    
    Returns:
        dict: Results with retry attempts and outcomes
    """
    results = {
        'checked': 0,
        'retried': 0,
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    # Get out-of-sync items
    query = XeroLastUpdate.objects.filter(out_of_sync=True)
    
    if tenant_id:
        try:
            tenant = XeroTenant.objects.get(tenant_id=tenant_id)
            query = query.filter(organisation=tenant)
        except XeroTenant.DoesNotExist:
            logger.error(f"Tenant {tenant_id} not found")
            return results
    
    # Filter by age - only retry items that haven't been out of sync too long
    cutoff_time = timezone.now() - timedelta(hours=max_retry_age_hours)
    query = query.filter(
        end_time__gte=cutoff_time
    ) if query.exists() else query.none()
    
    out_of_sync_items = query.select_related('organisation')
    
    results['checked'] = out_of_sync_items.count()
    logger.info(f"Found {results['checked']} out-of-sync items to check")
    
    for item in out_of_sync_items:
        tenant_id = item.organisation.tenant_id
        endpoint = item.end_point
        
        detail = {
            'tenant_id': tenant_id,
            'tenant_name': item.organisation.tenant_name,
            'endpoint': endpoint,
            'status': 'skipped',
            'error': None
        }
        
        try:
            # Determine retry action based on endpoint
            if endpoint in ['accounts', 'contacts', 'tracking_categories']:
                # Retry metadata update
                logger.info(f"Retrying metadata update for {endpoint} (tenant {tenant_id})")
                from apps.xero.xero_metadata.services import update_metadata
                result = update_metadata(tenant_id)
                
                if result.get('success'):
                    detail['status'] = 'success'
                    results['successful'] += 1
                    logger.info(f"Successfully retried {endpoint} for tenant {tenant_id}")
                else:
                    detail['status'] = 'failed'
                    detail['error'] = result.get('message', 'Unknown error')
                    results['failed'] += 1
                    logger.warning(f"Failed to retry {endpoint} for tenant {tenant_id}: {detail['error']}")
            
            elif endpoint in ['journals', 'manual_journals']:
                # Retry data source update
                logger.info(f"Retrying data source update for {endpoint} (tenant {tenant_id})")
                from apps.xero.xero_core.services import XeroApiClient, XeroAccountingApi
                from apps.xero.xero_auth.models import XeroClientCredentials
                
                credentials = XeroClientCredentials.objects.filter(active=True).first()
                if not credentials:
                    detail['status'] = 'skipped'
                    detail['error'] = 'No active credentials found'
                    results['skipped'] += 1
                    continue
                
                api_client = XeroApiClient(credentials.user, tenant_id=tenant_id)
                xero_api = XeroAccountingApi(api_client, tenant_id)
                
                if endpoint == 'journals':
                    xero_api.journals(load_all=False).get()
                else:
                    xero_api.manual_journals(load_all=False).get()
                
                detail['status'] = 'success'
                results['successful'] += 1
                logger.info(f"Successfully retried {endpoint} for tenant {tenant_id}")
            
            elif endpoint == 'trail_balance':
                # Retry trail balance creation
                logger.info(f"Retrying trail balance creation (tenant {tenant_id})")
                process_xero_data(tenant_id)
                
                # Check if still out of sync
                updated_item = XeroLastUpdate.objects.get(
                    end_point='trail_balance',
                    organisation=item.organisation
                )
                
                if not updated_item.out_of_sync:
                    detail['status'] = 'success'
                    results['successful'] += 1
                    logger.info(f"Successfully retried trail balance for tenant {tenant_id}")
                else:
                    detail['status'] = 'failed'
                    detail['error'] = updated_item.error_message or 'Still out of sync'
                    results['failed'] += 1
                    logger.warning(f"Trail balance still out of sync for tenant {tenant_id}")
            
            elif endpoint == 'profit_loss':
                # Retry P&L processing and validation
                logger.info(f"Retrying P&L processing (tenant {tenant_id})")
                result = process_profit_loss(tenant_id)
                
                if result.get('success') and result.get('stats', {}).get('in_sync', False):
                    detail['status'] = 'success'
                    results['successful'] += 1
                    logger.info(f"Successfully retried P&L for tenant {tenant_id}")
                else:
                    detail['status'] = 'failed'
                    detail['error'] = result.get('message', 'P&L still out of sync')
                    results['failed'] += 1
                    logger.warning(f"P&L still out of sync for tenant {tenant_id}")
            
            else:
                # Unknown endpoint - skip
                detail['status'] = 'skipped'
                detail['error'] = f'Unknown endpoint: {endpoint}'
                results['skipped'] += 1
                logger.warning(f"Skipping unknown endpoint {endpoint} for tenant {tenant_id}")
            
            results['retried'] += 1
        
        except Exception as e:
            detail['status'] = 'failed'
            detail['error'] = str(e)
            results['failed'] += 1
            logger.error(f"Error retrying {endpoint} for tenant {tenant_id}: {str(e)}", exc_info=True)
        
        results['details'].append(detail)
    
    logger.info(
        f"Out-of-sync check complete: {results['checked']} checked, "
        f"{results['retried']} retried, {results['successful']} successful, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )
    
    return results


def run_background_sync_check():
    """
    Background task to check and retry all out-of-sync items.
    This should be called periodically (e.g., every hour).
    """
    logger.info("Starting background sync check for all tenants")
    
    tenants = XeroTenant.objects.all()
    all_results = {
        'tenants_checked': 0,
        'total_checked': 0,
        'total_retried': 0,
        'total_successful': 0,
        'total_failed': 0,
        'total_skipped': 0,
    }
    
    for tenant in tenants:
        try:
            results = check_and_retry_out_of_sync(tenant_id=tenant.tenant_id)
            all_results['tenants_checked'] += 1
            all_results['total_checked'] += results['checked']
            all_results['total_retried'] += results['retried']
            all_results['total_successful'] += results['successful']
            all_results['total_failed'] += results['failed']
            all_results['total_skipped'] += results['skipped']
        except Exception as e:
            logger.error(f"Error checking tenant {tenant.tenant_id}: {str(e)}", exc_info=True)
    
    logger.info(
        f"Background sync check complete: {all_results['tenants_checked']} tenants checked, "
        f"{all_results['total_checked']} items checked, {all_results['total_retried']} retried, "
        f"{all_results['total_successful']} successful, {all_results['total_failed']} failed"
    )
    
    return all_results

