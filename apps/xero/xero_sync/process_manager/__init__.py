"""
Process Dependency Manager Package.

This package provides a flexible process dependency management system
with support for dependencies, caching, and validation.
"""
from .core import (
    ProcessDependencyManager,
    ProcessNode,
    ProcessStatus,
)

from .xero import (
    check_xero_sync_status,
    create_xero_sync_instance,
)

from .wrapper import ProcessManagerInstance
from .tree_builder import ProcessTreeBuilder, ProcessTreeManager, ProcessTreeInstance
from .xero_builder import build_xero_sync_tree
from .outdated_checkers import (
    check_journals_outdated,
    check_metadata_outdated,
    check_data_source_outdated,
    create_journals_outdated_checker,
    create_metadata_outdated_checker,
    create_data_source_outdated_checker,
    data_outdated_checker,
    create_data_outdated_checker,
)

from .trigger_utils import (
    fire_trigger,
    reset_trigger,
    subscribe_tree_to_trigger,
    unsubscribe_tree_from_trigger,
    get_trigger_subscriptions,
    get_tree_subscription,
    set_trigger_state,
)

from .trigger_decorators import (
    register_to_trigger,
    register_tree_to_trigger,
)

__all__ = [
    'ProcessDependencyManager',
    'ProcessNode',
    'ProcessStatus',
    'ProcessManagerInstance',
    'ProcessTreeBuilder',
    'ProcessTreeManager',
    'ProcessTreeInstance',
    'check_xero_sync_status',
    'create_xero_sync_instance',
    'build_xero_sync_tree',
    'check_journals_outdated',
    'check_metadata_outdated',
    'check_data_source_outdated',
    'create_journals_outdated_checker',
    'create_metadata_outdated_checker',
    'create_data_source_outdated_checker',
    'data_outdated_checker',
    'create_data_outdated_checker',
    'fire_trigger',
    'reset_trigger',
    'subscribe_tree_to_trigger',
    'unsubscribe_tree_from_trigger',
    'get_trigger_subscriptions',
    'get_tree_subscription',
    'set_trigger_state',
    'register_to_trigger',
    'register_tree_to_trigger',
]

