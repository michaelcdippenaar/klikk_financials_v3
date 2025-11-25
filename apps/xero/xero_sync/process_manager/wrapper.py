"""
Process Manager Wrapper Class.

Provides a convenient class-based interface for ProcessDependencyManager
with automatic attribute registration and method generation.
"""
import logging
from typing import Dict, List, Any, Callable, Optional
from .core import ProcessDependencyManager, ProcessStatus

logger = logging.getLogger(__name__)


class ProcessManagerInstance:
    """
    Wrapper class for ProcessDependencyManager that provides:
    - Automatic attribute registration from process tree
    - Method generation for each process
    - Convenient access to results and status
    """
    
    def __init__(
        self,
        process_trees: Dict[str, Dict[str, Dict[str, Any]]],
        cache_enabled: bool = True,
        response_variables: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None
    ):
        """
        Initialize ProcessManagerInstance.
        
        Args:
            process_trees: Dict mapping tree names to process definitions
            cache_enabled: Whether to enable caching
            response_variables: Optional dict mapping tree names to response variable definitions
        """
        # Initialize the core manager
        self.manager = ProcessDependencyManager(process_trees, cache_enabled=cache_enabled)
        
        # Store process trees for reference
        self.process_trees = process_trees
        
        # Register response variables if provided
        if response_variables:
            for tree_name, variables in response_variables.items():
                self.manager.register_response_variables(tree_name, variables)
        
        # Track registered attributes and methods (initialize before registration)
        self.registered_attributes: List[str] = []
        self.registered_methods: List[str] = []
        
        # Register attributes from process trees
        self._register_attributes()
        
        # Generate methods for each process
        self._generate_methods()
    
    def _register_attributes(self):
        """Register attributes from process trees."""
        for tree_name, processes in self.process_trees.items():
            for process_name in processes.keys():
                # Register status attribute
                attr_name = f"{process_name}_status"
                setattr(self, attr_name, ProcessStatus.PENDING)
                self.registered_attributes.append(attr_name)
                
                # Register result attribute
                attr_name = f"{process_name}_result"
                setattr(self, attr_name, None)
                self.registered_attributes.append(attr_name)
                
                # Register error attribute
                attr_name = f"{process_name}_error"
                setattr(self, attr_name, None)
                self.registered_attributes.append(attr_name)
                
                # Register execution_time attribute
                attr_name = f"{process_name}_execution_time"
                setattr(self, attr_name, None)
                self.registered_attributes.append(attr_name)
                
                # Register cached attribute
                attr_name = f"{process_name}_cached"
                setattr(self, attr_name, False)
                self.registered_attributes.append(attr_name)
    
    def _generate_methods(self):
        """Generate methods for each process in each tree."""
        for tree_name, processes in self.process_trees.items():
            for process_name in processes.keys():
                # Generate execute method for this process
                method_name = f"execute_{process_name}"
                if not hasattr(self, method_name):
                    setattr(self, method_name, self._create_execute_method(tree_name, process_name))
                    self.registered_methods.append(method_name)
                
                # Generate get_status method
                method_name = f"get_{process_name}_status"
                if not hasattr(self, method_name):
                    setattr(self, method_name, self._create_get_status_method(tree_name, process_name))
                    self.registered_methods.append(method_name)
                
                # Generate get_result method
                method_name = f"get_{process_name}_result"
                if not hasattr(self, method_name):
                    setattr(self, method_name, self._create_get_result_method(tree_name, process_name))
                    self.registered_methods.append(method_name)
    
    def _create_execute_method(self, tree_name: str, process_name: str) -> Callable:
        """Create an execute method for a specific process."""
        def execute_process(**kwargs):
            """Execute this specific process."""
            # Execute the entire tree (manager will handle dependencies)
            results = self.manager.execute(
                tree_name,
                context=kwargs,
                stop_on_error=True,
                skip_cached=True
            )
            
            # Update instance attributes
            self._update_attributes_from_results(tree_name, results)
            
            # Return result for this specific process
            return results.get('results', {}).get(process_name)
        
        return execute_process
    
    def _create_get_status_method(self, tree_name: str, process_name: str) -> Callable:
        """Create a get_status method for a specific process."""
        def get_status():
            """Get the status of this process."""
            return self.manager.get_process_status(tree_name, process_name)
        
        return get_status
    
    def _create_get_result_method(self, tree_name: str, process_name: str) -> Callable:
        """Create a get_result method for a specific process."""
        def get_result():
            """Get the result of this process."""
            try:
                return self.manager.get_process_result(tree_name, process_name)
            except ValueError:
                return None
        
        return get_result
    
    def _update_attributes_from_results(self, tree_name: str, results: Dict[str, Any]):
        """Update instance attributes from execution results."""
        status_dict = results.get('status', {})
        results_dict = results.get('results', {})
        errors_dict = results.get('errors', {})
        times_dict = results.get('execution_times', {})
        cached_dict = results.get('cached', {})
        
        for process_name in status_dict.keys():
            # Update status
            attr_name = f"{process_name}_status"
            if hasattr(self, attr_name):
                setattr(self, attr_name, status_dict.get(process_name))
            
            # Update result
            attr_name = f"{process_name}_result"
            if hasattr(self, attr_name):
                setattr(self, attr_name, results_dict.get(process_name))
            
            # Update error
            attr_name = f"{process_name}_error"
            if hasattr(self, attr_name):
                setattr(self, attr_name, errors_dict.get(process_name))
            
            # Update execution_time
            attr_name = f"{process_name}_execution_time"
            if hasattr(self, attr_name):
                setattr(self, attr_name, times_dict.get(process_name))
            
            # Update cached
            attr_name = f"{process_name}_cached"
            if hasattr(self, attr_name):
                setattr(self, attr_name, cached_dict.get(process_name, False))
    
    def execute_tree(
        self,
        tree_name: str,
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True,
        skip_cached: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a process tree.
        
        Args:
            tree_name: Name of the process tree to execute
            context: Optional context dict
            stop_on_error: If True, stop on first error
            skip_cached: If True, skip cached results
        
        Returns:
            Dict with execution results
        """
        results = self.manager.execute(
            tree_name,
            context=context or {},
            stop_on_error=stop_on_error,
            skip_cached=skip_cached
        )
        
        # Update instance attributes
        self._update_attributes_from_results(tree_name, results)
        
        return results
    
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
        Execute process tree with sync check.
        
        Args:
            tree_name: Name of the process tree
            sync_check_func: Function to check sync status
            context: Optional context dict
            stop_on_error: If True, stop on first error
            skip_cached: If True, skip cached results
            only_run_out_of_sync: If True, only run out-of-sync processes
        
        Returns:
            Dict with execution results including sync check
        """
        results = self.manager.execute_with_sync_check(
            tree_name,
            sync_check_func=sync_check_func,
            context=context or {},
            stop_on_error=stop_on_error,
            skip_cached=skip_cached,
            only_run_out_of_sync=only_run_out_of_sync
        )
        
        # Update instance attributes from execution results
        if 'execution' in results:
            self._update_attributes_from_results(tree_name, results['execution'])
        
        return results
    
    def get_execution_order(self, tree_name: str) -> List[str]:
        """Get execution order for a process tree."""
        return self.manager.get_execution_order(tree_name)
    
    def get_dependency_graph(self, tree_name: str) -> Dict[str, List[str]]:
        """Get dependency graph for a process tree."""
        return self.manager.get_dependency_graph(tree_name)
    
    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear cache entries."""
        self.manager.clear_cache(cache_key)
    
    def reset_tree(self, tree_name: str):
        """Reset a process tree to PENDING status."""
        self.manager.reset_process_tree(tree_name)
        # Reset instance attributes
        for process_name in self.process_trees.get(tree_name, {}).keys():
            setattr(self, f"{process_name}_status", ProcessStatus.PENDING)
            setattr(self, f"{process_name}_result", None)
            setattr(self, f"{process_name}_error", None)
            setattr(self, f"{process_name}_execution_time", None)
            setattr(self, f"{process_name}_cached", False)
    
    def get_all_results(self, tree_name: str) -> Dict[str, Any]:
        """Get all results for a process tree."""
        results = {}
        for process_name in self.process_trees.get(tree_name, {}).keys():
            try:
                results[process_name] = {
                    'status': getattr(self, f"{process_name}_status", None),
                    'result': getattr(self, f"{process_name}_result", None),
                    'error': getattr(self, f"{process_name}_error", None),
                    'execution_time': getattr(self, f"{process_name}_execution_time", None),
                    'cached': getattr(self, f"{process_name}_cached", False),
                }
            except AttributeError:
                pass
        return results
    
    def get_summary(self, tree_name: str) -> Dict[str, Any]:
        """Get a summary of execution status for a process tree."""
        summary = {
            'tree_name': tree_name,
            'processes': {},
            'overall_success': True,
            'total_processes': 0,
            'completed': 0,
            'failed': 0,
            'cached': 0,
            'pending': 0,
        }
        
        for process_name in self.process_trees.get(tree_name, {}).keys():
            status = getattr(self, f"{process_name}_status", ProcessStatus.PENDING)
            cached = getattr(self, f"{process_name}_cached", False)
            error = getattr(self, f"{process_name}_error", None)
            
            summary['processes'][process_name] = {
                'status': status.value if isinstance(status, ProcessStatus) else str(status),
                'cached': cached,
                'error': error,
            }
            
            summary['total_processes'] += 1
            
            if status == ProcessStatus.COMPLETED:
                summary['completed'] += 1
            elif status == ProcessStatus.CACHED:
                summary['cached'] += 1
                summary['completed'] += 1
            elif status == ProcessStatus.FAILED:
                summary['failed'] += 1
                summary['overall_success'] = False
            elif status == ProcessStatus.PENDING:
                summary['pending'] += 1
        
        return summary

