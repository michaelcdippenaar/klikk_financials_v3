# Process Tree Triggers Guide

Triggers provide a flexible way to determine if a process should run. They can be based on conditions, schedules, events, or custom logic.

## Overview

A **Trigger** is a database model that stores conditions and logic for determining when processes should execute. Triggers are checked before each process runs, and if a trigger doesn't fire (returns `False`), the process is skipped.

## Trigger Types

### 1. Condition Trigger
Checks if a context value meets certain conditions.

**Configuration:**
```json
{
  "field": "tenant_id",
  "operator": "equals",
  "value": "123"
}
```

**Operators:** `equals`, `not_equals`, `greater_than`, `less_than`, `exists`, `not_exists`

### 2. Schedule Trigger
Runs based on time intervals.

**Configuration:**
```json
{
  "interval_minutes": 60
}
```

### 3. Event Trigger
Runs when a specific event occurs.

**Configuration:**
```json
{
  "event_name": "data_updated"
}
```

### 4. Custom Function Trigger
Calls a custom Python function.

**Configuration:**
```json
{
  "function_ref": "apps.xero.xero_sync.process_manager.triggers.my_check_function"
}
```

### 5. Outdated Check Trigger
Checks if data is outdated (uses XeroLastUpdate).

**Configuration:**
```json
{
  "max_age_minutes": 60
}
```

## Usage Examples

### Creating a Trigger

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
from apps.xero.xero_sync.models import XeroLastUpdate

# Create process tree
tree = ProcessTreeInstance('my_tree', overwrite=True)

# Create a condition trigger
trigger = tree.create_trigger(
    name='tenant_check',
    trigger_type='condition',
    configuration={
        'field': 'tenant_id',
        'operator': 'equals',
        'value': '123'
    },
    description='Only run for tenant 123'
)

# Create an outdated check trigger
last_update = XeroLastUpdate.objects.get(name='journals_update')
outdated_trigger = tree.create_trigger(
    name='journals_outdated',
    trigger_type='outdated_check',
    xero_last_update_id=last_update.id,
    configuration={'max_age_minutes': 60},
    description='Run if journals data is older than 60 minutes'
)

# Add trigger to a process
tree.add_process(
    'sync_journals',
    func=my_function,
    dependencies=[],
    trigger='journals_outdated'  # Use trigger name
)

# Or add trigger after process is created
tree.add_trigger_to_process('sync_journals', 'journals_outdated')
```

### Using Triggers in Process Trees

```python
# Method 1: Pass trigger name when adding process
tree.add_process(
    'process_name',
    func=my_function,
    trigger='my_trigger_name'
)

# Method 2: Use outdated_check with trigger name via create_data_outdated_checker
from apps.xero.xero_sync.process_manager.outdated_checkers import create_data_outdated_checker

# Create trigger first
trigger = tree.create_trigger(
    name='journals_outdated_trigger',
    trigger_type='outdated_check',
    xero_last_update_id=last_update.id,
    configuration={'max_age_minutes': 60}
)

# Use trigger via outdated_check
outdated_checker = create_data_outdated_checker('journals_outdated_trigger')
tree.add_process(
    'process_name',
    func=my_function,
    outdated_check=outdated_checker  # Uses trigger
)

# Method 3: Add trigger after process is created
tree.add_trigger_to_process('process_name', 'my_trigger_name')
```

### Trigger Execution Flow

When a process tree executes:

1. **Cache Check** - If cached result exists and is valid, use it (skip trigger check)
2. **Trigger Check** - If trigger exists, call `trigger.should_trigger(context)`
   - If returns `False`: Skip process (status = SKIPPED)
   - If returns `True`: Continue to execution
3. **Outdated Check** - If `outdated_check` function exists, check it
4. **Execute** - Run the process function

### Trigger Methods

#### `should_trigger(context: dict) -> bool`
Main method to check if trigger should fire. Called automatically during execution.

#### `create_trigger(...)`
Create a new trigger for this process tree.

**Parameters:**
- `name`: Unique trigger name
- `trigger_type`: Type of trigger ('condition', 'schedule', 'event', 'custom', 'outdated_check')
- `configuration`: Trigger configuration dict
- `xero_last_update_id`: Optional XeroLastUpdate ID for outdated_check triggers
- `enabled`: Whether trigger is enabled (default: True)
- `description`: Description of the trigger

#### `add_trigger_to_process(process_name, trigger_name)`
Add a trigger to an existing process.

## Trigger vs Outdated Check

- **Trigger**: More flexible, can check any condition, stored in database
- **Outdated Check**: Function-based, checks if data is outdated, passed as callable

You can use both together - trigger is checked first, then outdated_check.

## Example: Complete Workflow

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
from apps.xero.xero_sync.models import XeroLastUpdate

# Create tree
tree = ProcessTreeInstance('scheduled_sync', overwrite=True)

# Get or create XeroLastUpdate
last_update, _ = XeroLastUpdate.objects.get_or_create(
    organisation=organisation,
    end_point='journals',
    defaults={'name': 'journals_update'}
)

# Create outdated check trigger
trigger = tree.create_trigger(
    name='journals_outdated_trigger',
    trigger_type='outdated_check',
    xero_last_update_id=last_update.id,
    configuration={'max_age_minutes': 30},
    description='Run if journals data is older than 30 minutes'
)

# Add process with trigger
tree.add_process(
    'sync_journals',
    func=sync_journals_function,
    dependencies=[],
    trigger='journals_outdated_trigger'
)

# Save tree
tree.save()

# When executed, the process will only run if:
# 1. Trigger fires (data is outdated)
# 2. No cached result exists
```

## Migration

After adding the Trigger model, run:

```bash
python manage.py migrate xero_sync
```

## Trigger Subscriptions and External Firing

### Overview

Triggers support a **subscription model** where multiple process trees can subscribe to the same trigger. When a trigger is fired (either automatically or manually by an external process), all subscribed trees are executed automatically.

This is different from the scheduler:
- **Scheduler**: Runs process trees on a time-based schedule
- **Trigger Subscriptions**: Process trees execute when a trigger fires (can be fired by external processes)

### Trigger States

Triggers have a `state` field that can be set by external processes:
- `pending`: Default state, trigger checks automatic conditions
- `fired`: Trigger has been manually fired, will execute subscribed trees
- `reset`: Reset to pending after checking

### Subscribing Trees to Triggers

#### Method 1: Using ProcessTreeInstance

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance

tree = ProcessTreeInstance('my_tree', overwrite=True)
# ... add processes ...

# Subscribe to a trigger
tree.subscribe_to_trigger('p&l_report_changed')

# Unsubscribe from a trigger
tree.unsubscribe_from_trigger('p&l_report_changed')
```

#### Method 2: Using Utility Functions

```python
from apps.xero.xero_sync.process_manager.trigger_utils import (
    subscribe_tree_to_trigger,
    unsubscribe_tree_from_trigger,
    get_trigger_subscriptions,
    get_tree_subscriptions
)

# Subscribe a tree to a trigger
subscribe_tree_to_trigger('my_tree', 'p&l_report_changed')

# Get all trees subscribed to a trigger
trees = get_trigger_subscriptions('p&l_report_changed')
print(trees)  # ['my_tree', 'another_tree']

# Get all triggers a tree is subscribed to
triggers = get_tree_subscriptions('my_tree')
print(triggers)  # ['p&l_report_changed', 'data_updated']
```

### Firing Triggers from External Processes

External processes (e.g., services, API endpoints, scheduled tasks) can fire triggers manually:

```python
from apps.xero.xero_sync.process_manager.trigger_utils import (
    fire_trigger,
    reset_trigger,
    set_trigger_state
)

# Fire a trigger - executes all subscribed trees
result = fire_trigger(
    'p&l_report_changed',
    context={'organisation': org, 'report_id': 123},
    fired_by='p&l_service'
)

print(result)
# {
#     'success': True,
#     'trigger': 'p&l_report_changed',
#     'fired_by': 'p&l_service',
#     'subscribed_trees': {
#         'tree1': {'success': True, ...},
#         'tree2': {'success': True, ...}
#     }
# }

# Reset trigger state after handling
reset_trigger('p&l_report_changed')

# Or set state manually
set_trigger_state('p&l_report_changed', 'fired')
```

### Example: Multiple Trees Subscribing to One Trigger

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
from apps.xero.xero_sync.process_manager.trigger_utils import (
    fire_trigger,
    subscribe_tree_to_trigger
)
from apps.xero.xero_sync.models import Trigger

# Create a shared trigger
trigger, _ = Trigger.objects.get_or_create(
    name='p&l_report_changed',
    defaults={
        'trigger_type': 'event',
        'description': 'Fired when P&L report changes',
        'enabled': True
    }
)

# Create first tree
tree1 = ProcessTreeInstance('p&l_tree_1', overwrite=True)
tree1.add_process('process_pnl', func=process_pnl_1, dependencies=[])
tree1.save()

# Create second tree
tree2 = ProcessTreeInstance('p&l_tree_2', overwrite=True)
tree2.add_process('process_pnl', func=process_pnl_2, dependencies=[])
tree2.save()

# Subscribe both trees to the trigger
subscribe_tree_to_trigger('p&l_tree_1', 'p&l_report_changed')
subscribe_tree_to_trigger('p&l_tree_2', 'p&l_report_changed')

# External process fires trigger - both trees execute
fire_trigger('p&l_report_changed', context={'organisation': org})
```

### Integration with Scheduler

The scheduler can run processes that fire triggers. For example:

```python
# In a scheduled task
def scheduled_pnl_check():
    """Check for P&L changes and fire trigger if needed."""
    if pnl_report_has_changed():
        fire_trigger('p&l_report_changed', fired_by='scheduler')
```

All subscribed trees will execute automatically when the trigger fires.

### Trigger Methods

#### `fire(context: dict, fired_by: str) -> dict`
Manually fire a trigger. Executes all subscribed trees.

**Returns:**
```python
{
    'success': bool,
    'trigger': str,  # Trigger name
    'fired_by': str,  # Who fired it
    'subscribed_trees': {  # Results from each tree
        'tree_name': {'success': bool, ...}
    }
}
```

#### `reset()`
Reset trigger state to 'pending'.

#### `subscribe_tree(tree_name: str)`
Subscribe a process tree to this trigger.

#### `unsubscribe_tree(tree_name: str)`
Unsubscribe a process tree from this trigger.

#### `execute_subscribed_trees(context: dict) -> dict`
Execute all subscribed trees (called automatically by `fire()`).

## Notes

- Triggers are checked before outdated_check functions
- If a trigger doesn't fire, the process is skipped (status = SKIPPED)
- Triggers can be enabled/disabled via the `enabled` field
- Trigger execution is logged (last_checked, last_triggered, trigger_count, last_fired_manually)
- Multiple processes can use the same trigger
- Multiple process trees can subscribe to the same trigger
- When a trigger fires, all subscribed trees execute automatically
- External processes can fire triggers manually using `fire_trigger()`
- The scheduler can run processes that fire triggers
- Triggers can be associated with a ProcessTree or used independently

