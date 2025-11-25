"""
Process Dependency Manager - Core implementation.

Manages processes with dependencies, caching, and validation.
"""
import logging
from typing import Dict, List, Any, Callable, Optional, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Status of a process execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


@dataclass
class ProcessNode:
    """Represents a single process node in the dependency tree."""
    name: str
    process_func: Callable
    dependencies: List[str] = field(default_factory=list)
    cache_key: Optional[str] = None
    cache_ttl: Optional[int] = None  # Time to live in seconds
    validation_func: Optional[Callable] = None
    required: bool = True  # If False, failure won't stop the workflow
    metadata: Dict[str, Any] = field(default_factory=dict)
    outdated_check: Optional[Callable] = None  # Function that returns True if data is outdated (should run)
    
    # Runtime state
    status: ProcessStatus = ProcessStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    cached: bool = False

class ProcessDependencyManager:
    """
    Manages processes with dependencies, caching, and validation.
    
    Example usage:
        manager = ProcessDependencyManager({
            'process_tree_name': {
                'process1': {
                    'func': my_function,
                    'dependencies': [],
                    'cache_key': 'process1_cache',
                    'validation': validate_func
                },
                'process2': {
                    'func': another_function,
                    'dependencies': ['process1'],
                    'required': True
                }
            }
        })
        
        results = manager.execute('process_tree_name')
    """
    
    def __init__(self, process_trees: Dict[str, Dict[str, Dict[str, Any]]], cache_enabled: bool = True):
        """
        Initialize the process dependency manager.
        
        Args:
            process_trees: Dict mapping tree names to process definitions.
                         Each process definition should have:
                         - 'func': Callable function to execute
                         - 'dependencies': List of process names this depends on
                         - 'cache_key': Optional cache key
                         - 'cache_ttl': Optional cache TTL in seconds
                         - 'validation': Optional validation function
                         - 'required': Whether process is required (default True)
                         - 'metadata': Optional metadata dict
            cache_enabled: Whether to enable caching (default True)
        """
        self.process_trees: Dict[str, Dict[str, ProcessNode]] = {}
        self.cache: Dict[str, Dict[str, Any]] = {}  # {cache_key: {result, timestamp, ttl}}
        self.cache_enabled = cache_enabled
        self.execution_order: Dict[str, List[str]] = {}  # Cached execution order per tree
        
        # Response attributes (set after execution)
        self.last_execution_results: Dict[str, Any] = {}
        self.last_execution_status: Dict[str, ProcessStatus] = {}
        self.last_execution_errors: Dict[str, str] = {}
        self.last_execution_times: Dict[str, float] = {}
        self.last_execution_cached: Dict[str, bool] = {}
        self.last_execution_success: bool = False
        
        # Process-specific response variables (initialized per process tree)
        self.process_response_variables: Dict[str, Dict[str, Any]] = {}
        
        # Registered methods list
        self.registered_methods: List[str] = []
        self._register_methods()
        
        # Registered response variables list
        self.registered_response_variables: List[str] = []
        
        # Build process nodes from definitions
        for tree_name, processes in process_trees.items():
            self.process_trees[tree_name] = self._build_process_nodes(processes)
            # Validate and calculate execution order
            self.execution_order[tree_name] = self._calculate_execution_order(tree_name)
    
    def _register_methods(self):
        """Register available methods to self.registered_methods."""
        self.registered_methods = [
            'execute',
            'get_execution_order',
            'get_process_status',
            'get_process_result',
            'clear_cache',
            'reset_process_tree',
            'get_dependency_graph',
            'add_process_tree',
            'remove_process_tree',
            'check_out_of_sync',
            'execute_with_sync_check',
            'register_response_variables',
            'get_response_variables',
        ]
    
    def register_response_variables(self, tree_name: str, response_variables: Dict[str, Dict[str, Any]]):
        """
        Register response variables with data types for a process tree.
        
        Args:
            tree_name: Name of the process tree
            response_variables: Dict mapping process names to their response variable definitions.
                              Format: {
                                  'process_name': {
                                      'variable_name': {
                                          'type': type_hint,
                                          'default': default_value,
                                          'description': 'Description'
                                      }
                                  }
                              }
        """
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        self.process_response_variables[tree_name] = response_variables
        
        # Initialize response variables as instance attributes
        for process_name, variables in response_variables.items():
            for var_name, var_def in variables.items():
                attr_name = f"{process_name}_{var_name}"
                default_value = var_def.get('default', None)
                setattr(self, attr_name, default_value)
                
                # Add to registered list
                if attr_name not in self.registered_response_variables:
                    self.registered_response_variables.append(attr_name)
    
    def get_response_variables(self, tree_name: str, process_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get response variable definitions for a process tree or specific process.
        
        Args:
            tree_name: Name of the process tree
            process_name: Optional process name. If provided, returns only that process's variables.
        
        Returns:
            Dict of response variable definitions
        """
        if tree_name not in self.process_response_variables:
            return {}
        
        if process_name:
            return self.process_response_variables[tree_name].get(process_name, {})
        else:
            return self.process_response_variables[tree_name]
    
    def _build_process_nodes(self, processes: Dict[str, Dict[str, Any]]) -> Dict[str, ProcessNode]:
        """Build ProcessNode objects from process definitions."""
        nodes = {}
        
        for name, config in processes.items():
            if 'func' not in config:
                raise ValueError(f"Process '{name}' must have a 'func' key")
            
            # Get trigger name from config
            trigger = config.get('trigger')
            metadata = config.get('metadata', {})
            if trigger:
                metadata['trigger'] = trigger
            
            node = ProcessNode(
                name=name,
                process_func=config['func'],
                dependencies=config.get('dependencies', []),
                cache_key=config.get('cache_key'),
                cache_ttl=config.get('cache_ttl'),
                validation_func=config.get('validation'),
                required=config.get('required', True),
                metadata=metadata,
                outdated_check=config.get('outdated_check')
            )
            
            nodes[name] = node
        
        return nodes
    
    def _calculate_execution_order(self, tree_name: str) -> List[str]:
        """
        Calculate the execution order using topological sort.
        Returns list of process names in execution order.
        """
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        nodes = self.process_trees[tree_name]
        
        # Build dependency graph
        in_degree = {name: 0 for name in nodes}
        graph = defaultdict(list)
        
        for name, node in nodes.items():
            for dep in node.dependencies:
                if dep not in nodes:
                    raise ValueError(f"Process '{name}' depends on '{dep}' which doesn't exist")
                graph[dep].append(name)
                in_degree[name] += 1
        
        # Topological sort using Kahn's algorithm
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        execution_order = []
        
        while queue:
            current = queue.popleft()
            execution_order.append(current)
            
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for circular dependencies
        if len(execution_order) != len(nodes):
            remaining = set(nodes.keys()) - set(execution_order)
            raise ValueError(f"Circular dependency detected. Processes not ordered: {remaining}")
        
        return execution_order
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if valid."""
        if not self.cache_enabled or cache_key not in self.cache:
            return None
        
        cached_data = self.cache[cache_key]
        ttl = cached_data.get('ttl')
        
        # Check if cache is expired
        if ttl is not None:
            age = time.time() - cached_data['timestamp']
            if age > ttl:
                del self.cache[cache_key]
                return None
        
        return cached_data['result']
    
    def _set_cache(self, cache_key: str, result: Any, ttl: Optional[int] = None):
        """Store result in cache."""
        if not self.cache_enabled:
            return
        
        self.cache[cache_key] = {
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl
        }
    
    def _validate_result(self, node: ProcessNode, result: Any) -> Tuple[bool, Optional[str]]:
        """Validate process result using validation function."""
        if node.validation_func is None:
            return True, None
        
        try:
            is_valid = node.validation_func(result)
            if isinstance(is_valid, bool):
                if is_valid:
                    return True, None
                else:
                    return False, "Validation function returned False"
            elif isinstance(is_valid, tuple):
                # Validation function can return (is_valid, error_message)
                return is_valid
            else:
                return False, f"Validation function returned unexpected type: {type(is_valid)}"
        except Exception as e:
            return False, f"Validation function raised exception: {str(e)}"
    
    def get_execution_order(self, tree_name: str) -> List[str]:
        """Get the execution order for a process tree."""
        if tree_name not in self.execution_order:
            raise ValueError(f"Process tree '{tree_name}' not found")
        return self.execution_order[tree_name].copy()
    
    def get_process_status(self, tree_name: str, process_name: str) -> Optional[ProcessStatus]:
        """Get the status of a specific process."""
        if tree_name not in self.process_trees:
            return None
        if process_name not in self.process_trees[tree_name]:
            return None
        return self.process_trees[tree_name][process_name].status
    
    def get_process_result(self, tree_name: str, process_name: str) -> Any:
        """Get the result of a specific process."""
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        if process_name not in self.process_trees[tree_name]:
            raise ValueError(f"Process '{process_name}' not found in tree '{tree_name}'")
        return self.process_trees[tree_name][process_name].result
    
    def clear_cache(self, cache_key: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            cache_key: If provided, clear only this cache key. Otherwise clear all.
        """
        if cache_key:
            if cache_key in self.cache:
                del self.cache[cache_key]
        else:
            self.cache.clear()
    
    def reset_process_tree(self, tree_name: str):
        """Reset all processes in a tree to PENDING status."""
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        for node in self.process_trees[tree_name].values():
            node.status = ProcessStatus.PENDING
            node.result = None
            node.error = None
            node.execution_time = None
            node.cached = False
    
    def execute(
        self,
        tree_name: str,
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True,
        skip_cached: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a process tree in dependency order.
        
        Args:
            tree_name: Name of the process tree to execute
            context: Optional context dict to pass to each process function
            stop_on_error: If True, stop execution on first error (default True)
            skip_cached: If True, skip processes with valid cached results (default True)
        
        Returns:
            Dict with execution results:
            {
                'success': bool,
                'results': {process_name: result},
                'status': {process_name: ProcessStatus},
                'errors': {process_name: error_message},
                'execution_times': {process_name: seconds},
                'cached': {process_name: bool}
            }
        """
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        if context is None:
            context = {}
        
        nodes = self.process_trees[tree_name]
        execution_order = self.execution_order[tree_name]
        
        results = {}
        status = {}
        errors = {}
        execution_times = {}
        cached = {}
        
        # Reset all nodes to PENDING
        self.reset_process_tree(tree_name)
        
        logger.info(f"Executing process tree '{tree_name}' with {len(execution_order)} processes")
        
        for process_name in execution_order:
            node = nodes[process_name]
            
            # Check cache first
            if skip_cached and node.cache_key:
                cached_result = self._get_from_cache(node.cache_key)
                if cached_result is not None:
                    node.status = ProcessStatus.CACHED
                    node.result = cached_result
                    node.cached = True
                    results[process_name] = cached_result
                    status[process_name] = ProcessStatus.CACHED
                    cached[process_name] = True
                    logger.info(f"Process '{process_name}' using cached result")
                    continue
            
            # Check trigger if present (process should only run if trigger fires)
            trigger_name = getattr(node, 'trigger', None) or node.metadata.get('trigger')
            if trigger_name:
                try:
                    from apps.xero.xero_sync.models import Trigger
                    
                    # Get trigger by name or ID
                    try:
                        if isinstance(trigger_name, int) or (isinstance(trigger_name, str) and trigger_name.isdigit()):
                            trigger = Trigger.objects.get(id=int(trigger_name))
                        else:
                            trigger = Trigger.objects.get(name=trigger_name)
                    except Trigger.DoesNotExist:
                        logger.warning(f"Trigger '{trigger_name}' not found for process '{process_name}'. Skipping trigger check.")
                        trigger = None
                    
                    if trigger:
                        # Prepare context for trigger check
                        check_context = {**context}
                        # Add dependency results to context
                        for dep_name in node.dependencies:
                            dep_node = nodes[dep_name]
                            if dep_node.result is not None:
                                check_context[dep_name] = dep_node.result
                        
                        should_trigger = trigger.should_trigger(check_context)
                        if not should_trigger:
                            node.status = ProcessStatus.SKIPPED
                            node.error = f"Trigger '{trigger.name}' did not fire"
                            status[process_name] = ProcessStatus.SKIPPED
                            errors[process_name] = f"Trigger '{trigger.name}' did not fire (should_trigger returned False)"
                            logger.info(f"Skipping process '{process_name}': trigger '{trigger.name}' did not fire")
                            continue
                        else:
                            logger.info(f"Process '{process_name}': trigger '{trigger.name}' fired, will execute")
                except Exception as e:
                    logger.warning(f"Error checking trigger for '{process_name}': {e}. Proceeding with execution.")
            
            # Check if data is outdated (only run if outdated_check returns True)
            if hasattr(node, 'outdated_check') and node.outdated_check is not None:
                try:
                    # Prepare context for outdated check
                    check_context = {**context}
                    # Add dependency results to context
                    for dep_name in node.dependencies:
                        dep_node = nodes[dep_name]
                        if dep_node.result is not None:
                            check_context[dep_name] = dep_node.result
                    
                    is_outdated = node.outdated_check(**check_context)
                    if not is_outdated:
                        node.status = ProcessStatus.SKIPPED
                        node.error = "Data is up-to-date"
                        status[process_name] = ProcessStatus.SKIPPED
                        errors[process_name] = "Data is up-to-date (outdated_check returned False)"
                        logger.info(f"Skipping process '{process_name}': data is up-to-date")
                        continue
                    else:
                        logger.info(f"Process '{process_name}': data is outdated, will execute")
                except Exception as e:
                    logger.warning(f"Error checking outdated status for '{process_name}': {e}. Proceeding with execution.")
            
            # Check if dependencies completed successfully
            dependency_failed = False
            for dep_name in node.dependencies:
                dep_node = nodes[dep_name]
                if dep_node.status == ProcessStatus.FAILED:
                    if node.required:
                        dependency_failed = True
                        break
                    else:
                        # Non-required process can continue even if dependency failed
                        logger.warning(
                            f"Process '{process_name}' dependency '{dep_name}' failed, "
                            f"but '{process_name}' is not required"
                        )
            
            if dependency_failed:
                node.status = ProcessStatus.SKIPPED
                node.error = "Dependency failed"
                status[process_name] = ProcessStatus.SKIPPED
                errors[process_name] = "Dependency failed"
                logger.warning(f"Skipping process '{process_name}' due to failed dependency")
                continue
            
            # Prepare arguments: include dependency results
            args = {}
            for dep_name in node.dependencies:
                dep_node = nodes[dep_name]
                if dep_node.result is not None:
                    args[dep_name] = dep_node.result
            
            # Merge with context
            process_context = {**context, **args}
            
            # Execute process
            node.status = ProcessStatus.RUNNING
            start_time = time.time()
            
            try:
                logger.info(f"Executing process '{process_name}'")
                
                # Call process function with context
                if isinstance(node.process_func, Callable):
                    result = node.process_func(**process_context)
                else:
                    raise ValueError(f"Process '{process_name}' func is not callable")
                
                node.execution_time = time.time() - start_time
                execution_times[process_name] = node.execution_time
                
                # Validate result
                is_valid, validation_error = self._validate_result(node, result)
                
                if not is_valid:
                    node.status = ProcessStatus.FAILED
                    node.error = validation_error or "Validation failed"
                    errors[process_name] = node.error
                    
                    if stop_on_error and node.required:
                        logger.error(f"Process '{process_name}' validation failed: {node.error}")
                        break
                    else:
                        logger.warning(f"Process '{process_name}' validation failed: {node.error}")
                        continue
                
                # Store result
                node.result = result
                node.status = ProcessStatus.COMPLETED
                results[process_name] = result
                status[process_name] = ProcessStatus.COMPLETED
                cached[process_name] = False
                
                # Update process-specific response variables if registered
                if tree_name in self.process_response_variables:
                    process_vars = self.process_response_variables[tree_name].get(process_name, {})
                    for var_name, var_def in process_vars.items():
                        attr_name = f"{process_name}_{var_name}"
                        # Extract value from result based on variable definition
                        if 'extract_func' in var_def:
                            value = var_def['extract_func'](result)
                        elif 'key' in var_def:
                            value = result.get(var_def['key']) if isinstance(result, dict) else None
                        else:
                            value = result  # Use entire result if no extraction defined
                        
                        setattr(self, attr_name, value)
                
                # Cache result if cache_key is set
                if node.cache_key:
                    self._set_cache(node.cache_key, result, node.cache_ttl)
                
                logger.info(f"Process '{process_name}' completed in {node.execution_time:.2f}s")
                
            except Exception as e:
                node.execution_time = time.time() - start_time
                node.status = ProcessStatus.FAILED
                node.error = str(e)
                errors[process_name] = str(e)
                execution_times[process_name] = node.execution_time
                
                logger.error(f"Process '{process_name}' failed: {str(e)}", exc_info=True)
                
                if stop_on_error and node.required:
                    break
        
        # Determine overall success
        success = all(
            nodes[name].status in [ProcessStatus.COMPLETED, ProcessStatus.CACHED]
            for name in execution_order
            if nodes[name].required
        )
        
        execution_result = {
            'success': success,
            'results': results,
            'status': {name: status.get(name, ProcessStatus.PENDING) for name in execution_order},
            'errors': errors,
            'execution_times': execution_times,
            'cached': cached
        }
        
        # Store as instance attributes
        self.last_execution_results = results
        self.last_execution_status = execution_result['status']
        self.last_execution_errors = errors
        self.last_execution_times = execution_times
        self.last_execution_cached = cached
        self.last_execution_success = success
        
        return execution_result
    
    def get_dependency_graph(self, tree_name: str) -> Dict[str, List[str]]:
        """Get the dependency graph for a process tree."""
        if tree_name not in self.process_trees:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        return {
            name: node.dependencies
            for name, node in self.process_trees[tree_name].items()
        }
    
    def add_process_tree(self, tree_name: str, processes: Dict[str, Dict[str, Any]]):
        """Add a new process tree."""
        self.process_trees[tree_name] = self._build_process_nodes(processes)
        self.execution_order[tree_name] = self._calculate_execution_order(tree_name)
    
    def remove_process_tree(self, tree_name: str):
        """Remove a process tree."""
        if tree_name in self.process_trees:
            del self.process_trees[tree_name]
        if tree_name in self.execution_order:
            del self.execution_order[tree_name]
    
    def check_out_of_sync(
        self,
        tree_name: str,
        sync_check_func: Callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if any processes in the tree are out of sync.
        
        This should be run first before executing any processes.
        Checks all endpoints and returns which ones are out of sync.
        
        Args:
            tree_name: Name of the process tree to check
            sync_check_func: Function that checks sync status.
                           Should return dict with 'out_of_sync' list and 'details' dict
                           Format: {
                               'out_of_sync': [list of process/endpoint names],
                               'details': {name: {'out_of_sync': bool, 'error': str}}
                           }
            context: Optional context dict
        
        Returns:
            Dict with sync check results:
            {
                'has_out_of_sync': bool,
                'out_of_sync': [list of out of sync process names],
                'details': {process_name: sync_details},
                'all_in_sync': bool
            }
        """
        if context is None:
            context = {}
        
        try:
            sync_result = sync_check_func(**context)
            
            out_of_sync_list = sync_result.get('out_of_sync', [])
            details = sync_result.get('details', {})
            
            return {
                'has_out_of_sync': len(out_of_sync_list) > 0,
                'out_of_sync': out_of_sync_list,
                'details': details,
                'all_in_sync': len(out_of_sync_list) == 0
            }
        except Exception as e:
            logger.error(f"Error checking sync status: {str(e)}", exc_info=True)
            return {
                'has_out_of_sync': True,
                'out_of_sync': ['sync_check_failed'],
                'details': {'sync_check_failed': {'out_of_sync': True, 'error': str(e)}},
                'all_in_sync': False
            }
    
    def execute_with_sync_check(
        self,
        tree_name: str,
        sync_check_func: Callable,
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True,
        skip_cached: bool = True,
        only_run_out_of_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Execute process tree with sync check first.
        
        Steps:
        1. Check all processes/endpoints for out-of-sync status
        2. If only_run_out_of_sync is True, only execute processes that are out of sync
           and their dependents. Otherwise, execute all processes.
        3. Execute processes in dependency order
        
        Args:
            tree_name: Name of the process tree to execute
            sync_check_func: Function to check sync status
            context: Optional context dict
            stop_on_error: If True, stop on first error
            skip_cached: If True, skip cached results
            only_run_out_of_sync: If True, only run out-of-sync processes and dependents
        
        Returns:
            Dict with execution results including sync check:
            {
                'sync_check': {...sync check results...},
                'execution': {...execution results...},
                'success': bool
            }
        """
        if context is None:
            context = {}
        
        # Step 1: Check sync status
        logger.info(f"Checking sync status for tree '{tree_name}'")
        sync_check_result = self.check_out_of_sync(tree_name, sync_check_func, context)
        
        # Step 2: Determine which processes to run
        processes_to_run = None
        if only_run_out_of_sync and sync_check_result['has_out_of_sync']:
            # Only run out-of-sync processes and their dependents
            out_of_sync_processes = set(sync_check_result['out_of_sync'])
            execution_order = self.execution_order[tree_name]
            
            # Find all processes that depend on out-of-sync processes
            processes_to_run = set()
            for process_name in execution_order:
                node = self.process_trees[tree_name][process_name]
                # Include if process is out of sync
                if process_name in out_of_sync_processes:
                    processes_to_run.add(process_name)
                # Include if any dependency is out of sync
                elif any(dep in out_of_sync_processes for dep in node.dependencies):
                    processes_to_run.add(process_name)
            
            logger.info(
                f"Found {len(out_of_sync_processes)} out-of-sync processes. "
                f"Will run {len(processes_to_run)} processes (including dependents)"
            )
        else:
            logger.info("Running all processes")
        
        # Step 3: Execute processes
        if processes_to_run is not None:
            # Temporarily filter execution order
            original_order = self.execution_order[tree_name]
            filtered_order = [p for p in original_order if p in processes_to_run]
            
            # Create temporary execution order
            original_execution_order = self.execution_order[tree_name]
            self.execution_order[tree_name] = filtered_order
            
            try:
                execution_result = self.execute(
                    tree_name,
                    context=context,
                    stop_on_error=stop_on_error,
                    skip_cached=skip_cached
                )
            finally:
                # Restore original execution order
                self.execution_order[tree_name] = original_execution_order
        else:
            execution_result = self.execute(
                tree_name,
                context=context,
                stop_on_error=stop_on_error,
                skip_cached=skip_cached
            )
        
        return {
            'sync_check': sync_check_result,
            'execution': execution_result,
            'success': execution_result['success'] and sync_check_result['all_in_sync']
        }

