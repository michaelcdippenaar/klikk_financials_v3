"""
Helper functions to check if data is outdated.

These functions return True if data is outdated (process should run),
False if data is up-to-date (process should skip).
"""
from typing import Dict, Any, Union, Optional
import logging

logger = logging.getLogger(__name__)


def check_journals_outdated(organisation, **context) -> bool:
    """
    Check if there are unprocessed journals that need to be processed.
    
    Args:
        organisation: XeroTenant organisation object
        **context: Additional context
    
    Returns:
        True if there are unprocessed journals (data is outdated), False otherwise
    """
    from apps.xero.xero_data.models import XeroJournalsSource
    
    unprocessed_count = XeroJournalsSource.objects.filter(
        organisation=organisation,
        processed=False
    ).count()
    
    is_outdated = unprocessed_count > 0
    
    if is_outdated:
        logger.info(f"Journals are outdated: {unprocessed_count} unprocessed journals found")
    else:
        logger.info("Journals are up-to-date: no unprocessed journals")
    
    return is_outdated


def check_metadata_outdated(organisation, **context) -> bool:
    """
    Check if metadata needs to be updated based on XeroLastUpdate status.
    
    Args:
        organisation: XeroTenant organisation object
        **context: Additional context
    
    Returns:
        True if metadata is outdated, False otherwise
    """
    from apps.xero.xero_sync.models import XeroLastUpdate
    
    metadata_endpoints = ['accounts', 'contacts', 'tracking_categories']
    
    for endpoint in metadata_endpoints:
        try:
            last_update = XeroLastUpdate.objects.get(
                end_point=endpoint,
                organisation=organisation
            )
            if not last_update.date:
                logger.info(f"Metadata outdated: {endpoint} never updated")
                return True
        except XeroLastUpdate.DoesNotExist:
            logger.info(f"Metadata outdated: {endpoint} never updated")
            return True
    
    logger.info("Metadata is up-to-date")
    return False


def check_data_source_outdated(organisation, endpoint: str, **context) -> bool:
    """
    Check if a specific data source endpoint is outdated.
    
    Args:
        organisation: XeroTenant organisation object
        endpoint: Endpoint name (e.g., 'journals', 'manual_journals')
        **context: Additional context
    
    Returns:
        True if data source is outdated, False otherwise
    """
    from apps.xero.xero_sync.models import XeroLastUpdate
    
    try:
        last_update = XeroLastUpdate.objects.get(
            end_point=endpoint,
            organisation=organisation
        )
        if not last_update.date:
            logger.info(f"Data source '{endpoint}' is outdated (never updated)")
            return True
    except XeroLastUpdate.DoesNotExist:
        logger.info(f"Data source '{endpoint}' never updated")
        return True
    
    logger.info(f"Data source '{endpoint}' is up-to-date")
    return False


def create_journals_outdated_checker(organisation):
    """
    Create a closure that checks if journals are outdated for a specific organisation.
    
    Args:
        organisation: XeroTenant organisation object
    
    Returns:
        Function that can be used as outdated_check parameter
    """
    def check(**context) -> bool:
        return check_journals_outdated(organisation, **context)
    
    return check


def create_metadata_outdated_checker(organisation):
    """
    Create a closure that checks if metadata is outdated for a specific organisation.
    
    Args:
        organisation: XeroTenant organisation object
    
    Returns:
        Function that can be used as outdated_check parameter
    """
    def check(**context) -> bool:
        return check_metadata_outdated(organisation, **context)
    
    return check


def create_data_source_outdated_checker(organisation, endpoint: str):
    """
    Create a closure that checks if a data source is outdated for a specific organisation.
    
    Args:
        organisation: XeroTenant organisation object
        endpoint: Endpoint name (e.g., 'journals', 'manual_journals')
    
    Returns:
        Function that can be used as outdated_check parameter
    """
    def check(**context) -> bool:
        return check_data_source_outdated(organisation, endpoint, **context)
    
    return check


def data_outdated_checker(identifier: Union[str, int, 'XeroLastUpdate'], **context) -> bool:
    """
    Check if data is outdated based on XeroLastUpdate record.
    Can be identified by name (str), ID (int), or XeroLastUpdate instance.
    
    Args:
        identifier: Can be:
                   - str: Name of the XeroLastUpdate record
                   - int: ID of the XeroLastUpdate record
                   - XeroLastUpdate: Instance of XeroLastUpdate model
        **context: Additional context
    
    Returns:
        True if data is outdated (process should run), False if up-to-date (process should skip)
    
    Raises:
        ValueError: If identifier not found or invalid
    """
    from apps.xero.xero_sync.models import XeroLastUpdate
    
    # If identifier is already a XeroLastUpdate instance
    if isinstance(identifier, XeroLastUpdate):
        last_update = identifier
    # If identifier is an integer (ID)
    elif isinstance(identifier, int):
        try:
            last_update = XeroLastUpdate.objects.get(id=identifier)
        except XeroLastUpdate.DoesNotExist:
            raise ValueError(f"XeroLastUpdate with ID {identifier} not found")
    # If identifier is a string (name)
    elif isinstance(identifier, str):
        try:
            last_update = XeroLastUpdate.objects.get(name=identifier)
        except XeroLastUpdate.DoesNotExist:
            raise ValueError(f"XeroLastUpdate with name '{identifier}' not found")
    else:
        raise ValueError(f"Invalid identifier type: {type(identifier)}. Must be str (name), int (ID), or XeroLastUpdate instance")
    
    # Check if data is outdated
    if not last_update.date:
        logger.info(f"Data outdated for '{last_update.name or last_update.end_point}' (org: {last_update.organisation.tenant_name}): never updated")
        return True
    
    logger.info(f"Data up-to-date for '{last_update.name or last_update.end_point}' (org: {last_update.organisation.tenant_name})")
    return False


def create_data_outdated_checker(trigger_name: str):
    """
    Create a closure that checks if data is outdated using a Trigger.
    The trigger name is used to look up the trigger, which then determines if data is outdated.
    
    Args:
        trigger_name: Name of the Trigger record
    
    Returns:
        Function that can be used as outdated_check parameter
    
    Example:
        # Using trigger name
        checker = create_data_outdated_checker('journals_outdated_trigger')
        
        # Use in process tree
        tree.add_process(
            'sync_journals',
            func=my_function,
            outdated_check=checker
        )
    
    Raises:
        ValueError: If trigger not found
    """
    from apps.xero.xero_sync.models import Trigger
    
    # Look up trigger by name
    try:
        trigger = Trigger.objects.get(name=trigger_name)
    except Trigger.DoesNotExist:
        raise ValueError(f"Trigger with name '{trigger_name}' not found")
    
    def check(**context) -> bool:
        """Check if trigger should fire (data is outdated)."""
        return trigger.should_trigger(context)
    
    return check

