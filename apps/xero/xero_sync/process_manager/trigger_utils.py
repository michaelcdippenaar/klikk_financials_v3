"""
Utility functions for managing triggers from external processes.
This module provides a clean API for external processes to fire triggers
and manage trigger subscriptions.
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def fire_trigger(trigger_name: str, context: Dict[str, Any] = None, fired_by: str = None) -> Dict[str, Any]:
    """
    Fire a trigger manually (for external processes).
    This will execute all process trees subscribed to the trigger.
    
    Args:
        trigger_name: Name of the trigger to fire
        context: Optional context dict to pass to subscribed trees
        fired_by: Optional identifier of what fired this trigger (for logging)
    
    Returns:
        Dict with execution results for all subscribed trees
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import fire_trigger
        >>> result = fire_trigger(
        ...     'p&l_report_changed',
        ...     context={'organisation': org, 'report_id': 123},
        ...     fired_by='p&l_service'
        ... )
        >>> print(result['success'])
        True
    """
    from apps.xero.xero_sync.models import Trigger
    
    try:
        trigger = Trigger.objects.get(name=trigger_name)
        return trigger.fire(context=context, fired_by=fired_by)
    except Trigger.DoesNotExist:
        error_msg = f"Trigger '{trigger_name}' not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Error firing trigger '{trigger_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


def reset_trigger(trigger_name: str) -> bool:
    """
    Reset a trigger state to 'pending'.
    Useful for external processes to reset trigger after handling.
    
    Args:
        trigger_name: Name of the trigger to reset
    
    Returns:
        True if successful, False otherwise
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import reset_trigger
        >>> reset_trigger('p&l_report_changed')
        True
    """
    from apps.xero.xero_sync.models import Trigger
    
    try:
        trigger = Trigger.objects.get(name=trigger_name)
        trigger.reset()
        return True
    except Trigger.DoesNotExist:
        logger.error(f"Trigger '{trigger_name}' not found")
        return False
    except Exception as e:
        logger.error(f"Error resetting trigger '{trigger_name}': {str(e)}", exc_info=True)
        return False


def subscribe_tree_to_trigger(tree_name: str, trigger_name: str) -> bool:
    """
    Subscribe a process tree to a trigger.
    When the trigger fires, the tree will be executed.
    
    Args:
        tree_name: Name of the ProcessTree to subscribe
        trigger_name: Name of the Trigger to subscribe to
    
    Returns:
        True if successful, False otherwise
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import subscribe_tree_to_trigger
        >>> subscribe_tree_to_trigger('my_process_tree', 'p&l_report_changed')
        True
    """
    from apps.xero.xero_sync.models import Trigger, ProcessTree
    
    try:
        trigger = Trigger.objects.get(name=trigger_name)
        tree = ProcessTree.objects.get(name=tree_name)
        tree.trigger = trigger
        tree.save(update_fields=['trigger'])
        logger.info(f"Subscribed tree '{tree_name}' to trigger '{trigger_name}'")
        return True
    except Trigger.DoesNotExist:
        logger.error(f"Trigger '{trigger_name}' not found")
        return False
    except ProcessTree.DoesNotExist:
        logger.error(f"ProcessTree '{tree_name}' not found")
        return False
    except Exception as e:
        logger.error(f"Error subscribing tree '{tree_name}' to trigger '{trigger_name}': {str(e)}", exc_info=True)
        return False


def unsubscribe_tree_from_trigger(tree_name: str) -> bool:
    """
    Unsubscribe a process tree from its current trigger.
    
    Args:
        tree_name: Name of the ProcessTree to unsubscribe
    
    Returns:
        True if successful, False otherwise
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import unsubscribe_tree_from_trigger
        >>> unsubscribe_tree_from_trigger('my_process_tree')
        True
    """
    from apps.xero.xero_sync.models import ProcessTree
    
    try:
        tree = ProcessTree.objects.get(name=tree_name)
        if tree.trigger:
            trigger_name = tree.trigger.name
            tree.trigger = None
            tree.save(update_fields=['trigger'])
            logger.info(f"Unsubscribed tree '{tree_name}' from trigger '{trigger_name}'")
            return True
        else:
            logger.warning(f"Tree '{tree_name}' is not subscribed to any trigger")
            return False
    except ProcessTree.DoesNotExist:
        logger.error(f"ProcessTree '{tree_name}' not found")
        return False
    except Exception as e:
        logger.error(f"Error unsubscribing tree '{tree_name}': {str(e)}", exc_info=True)
        return False


def get_trigger_subscriptions(trigger_name: str) -> List[str]:
    """
    Get list of process tree names subscribed to a trigger.
    
    Args:
        trigger_name: Name of the trigger
    
    Returns:
        List of process tree names subscribed to the trigger
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import get_trigger_subscriptions
        >>> trees = get_trigger_subscriptions('p&l_report_changed')
        >>> print(trees)
        ['tree1', 'tree2']
    """
    from apps.xero.xero_sync.models import Trigger
    
    try:
        trigger = Trigger.objects.get(name=trigger_name)
        return list(trigger.process_trees.values_list('name', flat=True))
    except Trigger.DoesNotExist:
        logger.error(f"Trigger '{trigger_name}' not found")
        return []
    except Exception as e:
        logger.error(f"Error getting subscriptions for trigger '{trigger_name}': {str(e)}", exc_info=True)
        return []


def get_tree_subscription(tree_name: str) -> Optional[str]:
    """
    Get the trigger name that a process tree is subscribed to.
    
    Args:
        tree_name: Name of the process tree
    
    Returns:
        Trigger name if subscribed, None otherwise
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import get_tree_subscription
        >>> trigger = get_tree_subscription('my_process_tree')
        >>> print(trigger)
        'p&l_report_changed'
    """
    from apps.xero.xero_sync.models import ProcessTree
    
    try:
        tree = ProcessTree.objects.get(name=tree_name)
        return tree.trigger.name if tree.trigger else None
    except ProcessTree.DoesNotExist:
        logger.error(f"ProcessTree '{tree_name}' not found")
        return None
    except Exception as e:
        logger.error(f"Error getting subscription for tree '{tree_name}': {str(e)}", exc_info=True)
        return None


def set_trigger_state(trigger_name: str, state: str) -> bool:
    """
    Set trigger state manually (for external processes).
    Valid states: 'pending', 'fired', 'reset'
    
    Args:
        trigger_name: Name of the trigger
        state: New state ('pending', 'fired', 'reset')
    
    Returns:
        True if successful, False otherwise
    
    Example:
        >>> from apps.xero.xero_sync.process_manager.trigger_utils import set_trigger_state
        >>> set_trigger_state('p&l_report_changed', 'fired')
        True
    """
    from apps.xero.xero_sync.models import Trigger
    
    valid_states = ['pending', 'fired', 'reset']
    if state not in valid_states:
        logger.error(f"Invalid state '{state}'. Must be one of: {valid_states}")
        return False
    
    try:
        trigger = Trigger.objects.get(name=trigger_name)
        trigger.state = state
        trigger.save(update_fields=['state'])
        logger.info(f"Set trigger '{trigger_name}' state to '{state}'")
        return True
    except Trigger.DoesNotExist:
        logger.error(f"Trigger '{trigger_name}' not found")
        return False
    except Exception as e:
        logger.error(f"Error setting trigger '{trigger_name}' state: {str(e)}", exc_info=True)
        return False

