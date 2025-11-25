# Process Tree Scheduling Guide

This guide explains how to register process trees with the task scheduler and create management commands for them.

## Overview

Process trees can now be:
1. **Scheduled** to run automatically via APScheduler
2. **Registered** with the task scheduler using `register_schedule()`
3. **Executed** via management commands created with `create_command()`

## Quick Start

### 1. Create and Register a Process Tree

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
import datetime

# Create your process tree
tree = ProcessTreeInstance('my_scheduled_tree', overwrite=True)
tree.add_process('step1', func=my_function, dependencies=[])

# Save the tree
tree.save()

# Register with scheduler (runs every 60 minutes)
schedule = tree.register_schedule(
    interval_minutes=60,
    start_time=datetime.time(0, 0),  # Start at midnight
    enabled=True,
    context={'tenant_id': '123'}  # Default context
)

print(f"Scheduled! Next run: {schedule.next_run}")
```

### 2. Create a Management Command

```python
# Generate a Django management command
command_path = tree.create_command()
# Output: apps/xero/xero_sync/management/commands/my_scheduled_tree.py

# Now you can run:
# python manage.py my_scheduled_tree --context '{"tenant_id": "123"}'
```

## Methods

### `register_schedule()`

Register a process tree with the task scheduler.

**Parameters:**
- `interval_minutes` (int): Minutes between executions (default: 60)
- `start_time` (datetime.time): Preferred start time (default: midnight)
- `enabled` (bool): Whether scheduling is enabled (default: True)
- `context` (dict): Default context to pass to executions (default: {})

**Returns:** `ProcessTreeSchedule` instance

**Example:**
```python
schedule = tree.register_schedule(
    interval_minutes=30,  # Run every 30 minutes
    start_time=datetime.time(9, 0),  # Start at 9 AM
    context={'organisation': my_org}
)
```

### `create_command()`

Generate a Django management command file for running the process tree.

**Parameters:**
- `command_name` (str, optional): Name for the command (defaults to tree name)
- `output_path` (str, optional): Path to write command file (defaults to `management/commands/`)

**Returns:** Path to the created command file

**Example:**
```python
# Create command with default name
command_path = tree.create_command()

# Create command with custom name
command_path = tree.create_command(command_name='run_my_tree')

# Create command in custom location
command_path = tree.create_command(output_path='/path/to/commands/')
```

### `create_task_function()`

Create a task function that can be used directly with APScheduler.

**Returns:** Callable function

**Example:**
```python
task_func = tree.create_task_function()

# Use with APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()
scheduler.add_job(
    task_func,
    trigger=IntervalTrigger(minutes=60),
    id=f'process_tree_{tree.name}'
)
scheduler.start()
```

## ProcessTreeSchedule Model

The `ProcessTreeSchedule` model stores scheduling configuration:

- `process_tree`: OneToOne relationship to ProcessTree
- `enabled`: Enable/disable scheduling
- `interval_minutes`: Minutes between executions
- `start_time`: Preferred start time
- `last_run`: Last execution time
- `next_run`: Next scheduled execution time
- `context`: Default context dict

### Methods

- `should_run()`: Check if process tree should run now
- `update_next_run_time()`: Calculate and update next run time

## Automatic Execution

Once registered, process trees are automatically checked and executed by the scheduler:

1. The `check_and_run_scheduled_tasks()` function runs every minute
2. It checks all enabled `ProcessTreeSchedule` instances
3. If `should_run()` returns True, it executes the process tree
4. The schedule's `last_run` and `next_run` are updated automatically

## Example: Complete Workflow

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeInstance
from apps.xero.xero_core.models import XeroTenant
import datetime

# 1. Create process tree
tree = ProcessTreeInstance('hourly_journals_sync', overwrite=True)

organisation = XeroTenant.objects.first()

def sync_journals(**context):
    org = context.get('organisation', organisation)
    # Your sync logic here
    return {'status': 'success'}

tree.add_function('sync_journals', sync_journals)
tree.add_process('sync', func=sync_journals, dependencies=[])

# 2. Save tree
tree.save()

# 3. Register with scheduler
schedule = tree.register_schedule(
    interval_minutes=60,
    start_time=datetime.time(0, 0),
    enabled=True,
    context={'organisation': organisation}
)

# 4. Create management command (optional)
command_path = tree.create_command()
print(f"Command created: {command_path}")

# 5. The scheduler will now automatically run this tree every hour!
```

## Running Manually

You can also run scheduled process trees manually:

### Via Management Command

```bash
python manage.py my_scheduled_tree
python manage.py my_scheduled_tree --context '{"tenant_id": "123"}'
```

### Via Python

```python
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeManager

results = ProcessTreeManager.execute_tree(
    'my_scheduled_tree',
    context={'tenant_id': '123'}
)
```

## Migration

After adding the `ProcessTreeSchedule` model, run:

```bash
python manage.py migrate xero_sync
```

## Notes

- Process trees must be saved before registering schedules
- The scheduler checks for due tasks every minute
- Functions used in process trees should be registered via `add_function()` or available in the `func_registry`
- Context passed to `register_schedule()` becomes the default context for all executions
- You can override context when running manually via management command

