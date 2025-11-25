"""
Decorators for registering process trees to triggers.

This module provides decorators that allow process trees to be automatically
registered to triggers when they are created.
"""
import functools
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def register_to_trigger(trigger_name: str):
    """
    Decorator to register a process tree to a trigger.
    
    Usage:
        @register_to_trigger('p&l_report_changed')
        def example_build_and_save_tree():
            tree = ProcessTreeInstance('my_tree', overwrite=True)
            # ... build tree ...
            return tree.save()
    
    Args:
        trigger_name: Name of the trigger to register the process tree to
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the function to get the process tree
            result = func(*args, **kwargs)
            
            # If result is a ProcessTreeInstance, register it to the trigger
            from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
            from apps.xero.xero_sync.models import Trigger
            
            if isinstance(result, ProcessTreeInstance):
                # Ensure tree is saved
                if not result._tree_model:
                    saved_tree = result.save()
                else:
                    saved_tree = result._tree_model
                
                # Get or create trigger
                try:
                    trigger = Trigger.objects.get(name=trigger_name)
                    # Subscribe tree to trigger
                    saved_tree.trigger = trigger
                    saved_tree.save(update_fields=['trigger'])
                    logger.info(f"Registered process tree '{saved_tree.name}' to trigger '{trigger_name}'")
                except Trigger.DoesNotExist:
                    logger.warning(f"Trigger '{trigger_name}' not found. Tree '{saved_tree.name}' not registered.")
            
            # If result is a ProcessTree model instance, register it directly
            elif hasattr(result, 'name') and hasattr(result, 'trigger'):
                from apps.xero.xero_sync.models import Trigger
                try:
                    trigger = Trigger.objects.get(name=trigger_name)
                    result.trigger = trigger
                    result.save(update_fields=['trigger'])
                    logger.info(f"Registered process tree '{result.name}' to trigger '{trigger_name}'")
                except Trigger.DoesNotExist:
                    logger.warning(f"Trigger '{trigger_name}' not found. Tree '{result.name}' not registered.")
            
            return result
        
        return wrapper
    return decorator


def register_tree_to_trigger(tree_name: str, trigger_name: str):
    """
    Helper function to register an existing process tree to a trigger.
    
    Args:
        tree_name: Name of the process tree
        trigger_name: Name of the trigger
    
    Returns:
        True if successful, False otherwise
    """
    from apps.xero.xero_sync.models import ProcessTree, Trigger
    
    try:
        tree = ProcessTree.objects.get(name=tree_name)
        trigger = Trigger.objects.get(name=trigger_name)
        tree.trigger = trigger
        tree.save(update_fields=['trigger'])
        logger.info(f"Registered process tree '{tree_name}' to trigger '{trigger_name}'")
        return True
    except ProcessTree.DoesNotExist:
        logger.error(f"ProcessTree '{tree_name}' not found")
        return False
    except Trigger.DoesNotExist:
        logger.error(f"Trigger '{trigger_name}' not found")
        return False

