"""
Process Tree Builder and Manager.

Allows building process trees programmatically and storing them in the database.
Supports dependent trees (sequential) and sibling trees (parallel/async).
"""
import logging
import inspect
import datetime
from typing import Dict, List, Any, Callable, Optional
from django.db import transaction
from django.utils import timezone
from apps.xero.xero_sync.models import ProcessTree
from .wrapper import ProcessManagerInstance

logger = logging.getLogger(__name__)


class ProcessTreeBuilder:
    """
    Builder class for creating process trees programmatically.
    Use this to build process trees and then save them to the database.
    """
    
    def __init__(self, name: str, description: str = "", cache_enabled: bool = True):
        """
        Initialize a process tree builder.
        
        Args:
            name: Unique name for the process tree
            description: Description of what this process tree does
            cache_enabled: Whether to enable caching
        """
        self.name = name
        self.description = description
        self.cache_enabled = cache_enabled
        self.processes: dict = {}
        self.response_variables: dict = {}
    
    def add(
        self,
        process_name: str,
        func: Callable,
        dependencies: List[str] = None,
        cache_key: str = None,
        cache_ttl: int = None,
        validation: Callable = None,
        required: bool = True,
        metadata: Dict[str, Any] = None,
        response_vars: Dict[str, Dict[str, Any]] = None
    ):
        """
        Add a process to the tree.
        
        Args:
            process_name: Name of the process
            func: Function to execute
            dependencies: List of process names this depends on
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL in seconds
            validation: Optional validation function
            required: Whether process is required (default True)
            metadata: Optional metadata dict
            response_vars: Optional response variable definitions for this process
        
        Returns:
            self (for method chaining)
        """
        if dependencies is None:
            dependencies = []
        if metadata is None:
            metadata = {}
        
        self.processes[process_name] = {
            'func': func,
            'dependencies': dependencies,
            'cache_key': cache_key,
            'cache_ttl': cache_ttl,
            'validation': validation,
            'required': required,
            'metadata': metadata
        }
        
        # Store response variables if provided
        if response_vars:
            self.response_variables[process_name] = response_vars
        
        return self  # Allow method chaining
    
    def build(self) -> Dict[str, Dict[str, Any]]:
        """
        Build the process tree dictionary.
        
        Returns:
            Dict with process tree structure
        """
        # Convert functions to serializable format
        process_tree_data = {}
        for process_name, process_def in self.processes.items():
            process_tree_data[process_name] = {
                'func': process_def['func'],  # Keep function reference for runtime
                'dependencies': process_def['dependencies'],
                'cache_key': process_def['cache_key'],
                'cache_ttl': process_def['cache_ttl'],
                'validation': process_def['validation'],
                'required': process_def['required'],
                'metadata': process_def['metadata']
            }
        
        return {self.name: process_tree_data}
    
    def save(self) -> ProcessTree:
        """
        Save the process tree to the database.
        Note: Functions are stored as references (module + name) since they can't be serialized.
        
        Returns:
            ProcessTree instance
        """
        process_tree_data = {}
        
        for process_name, process_def in self.processes.items():
            # Store function reference
            func = process_def['func']
            func_ref = self._get_function_ref(func)
            validation_ref = self._get_function_ref(process_def.get('validation'))
            
            process_tree_data[process_name] = {
                'func_ref': func_ref,
                'dependencies': process_def['dependencies'],
                'cache_key': process_def['cache_key'],
                'cache_ttl': process_def['cache_ttl'],
                'validation_ref': validation_ref,
                'required': process_def['required'],
                'metadata': process_def['metadata']
            }
        
        tree, created = ProcessTree.objects.update_or_create(
            name=self.name,
            defaults={
                'description': self.description,
                'process_tree_data': {self.name: process_tree_data},
                'response_variables': {self.name: self.response_variables} if self.response_variables else {},
                'cache_enabled': self.cache_enabled
            }
        )
        
        logger.info(f"{'Created' if created else 'Updated'} process tree '{self.name}'")
        return tree
    
    def _get_function_ref(self, func):
        """Get function reference for storage."""
        if func is None:
            return None
        if callable(func):
            return {
                'module': func.__module__ if hasattr(func, '__module__') else None,
                'name': func.__name__ if hasattr(func, '__name__') else str(func)
            }
        return func


class ProcessTreeManager:
    """
    Manager class for working with stored process trees.
    Handles loading from database, creating instances, and executing trees.
    """
    
    @staticmethod
    def get_tree(name: str) -> Optional[ProcessTree]:
        """Get a process tree by name."""
        try:
            return ProcessTree.objects.get(name=name, enabled=True)
        except ProcessTree.DoesNotExist:
            return None
    
    @staticmethod
    def create_instance(tree_name: str, func_registry: Dict[str, Callable] = None) -> ProcessManagerInstance:
        """
        Create a ProcessManagerInstance from a stored process tree.
        
        Args:
            tree_name: Name of the stored process tree
            func_registry: Dict mapping function references to actual callable functions.
                          If None, will try to import from module paths.
        
        Returns:
            ProcessManagerInstance configured with the process tree
        """
        tree = ProcessTreeManager.get_tree(tree_name)
        if not tree:
            raise ValueError(f"Process tree '{tree_name}' not found or disabled")
        
        # Load process tree data
        process_tree_data = tree.get_process_tree_dict()
        response_variables = tree.get_response_variables_dict()
        
        # Resolve function references to actual functions
        resolved_tree = ProcessTreeManager._resolve_functions(
            process_tree_data,
            func_registry or {}
        )
        
        # Create instance
        instance = ProcessManagerInstance(
            process_trees=resolved_tree,
            cache_enabled=tree.cache_enabled,
            response_variables=response_variables
        )
        
        return instance
    
    @staticmethod
    def _resolve_functions(process_tree_data: dict, func_registry: dict) -> dict:
        """Resolve function references to actual callable functions."""
        resolved_tree = {}
        
        for tree_name, processes in process_tree_data.items():
            resolved_processes = {}
            
            for process_name, process_def in processes.items():
                # Resolve function
                func_ref = process_def.get('func_ref') or process_def.get('func')
                if isinstance(func_ref, dict):
                    # Try to get from registry first
                    func_key = f"{func_ref.get('module')}.{func_ref.get('name')}"
                    func = func_registry.get(func_key) or func_registry.get(func_ref.get('name'))
                    
                    if not func:
                        # Try to import from module
                        try:
                            import importlib
                            module = importlib.import_module(func_ref['module'])
                            func = getattr(module, func_ref['name'])
                        except (ImportError, AttributeError) as e:
                            logger.error(f"Could not resolve function {func_key}: {e}")
                            raise ValueError(f"Could not resolve function {func_key}")
                else:
                    func = func_ref
                
                # Resolve validation function
                validation_ref = process_def.get('validation_ref') or process_def.get('validation')
                validation = None
                if validation_ref:
                    if isinstance(validation_ref, dict):
                        validation_key = f"{validation_ref.get('module')}.{validation_ref.get('name')}"
                        validation = func_registry.get(validation_key) or func_registry.get(validation_ref.get('name'))
                        if not validation:
                            try:
                                import importlib
                                module = importlib.import_module(validation_ref['module'])
                                validation = getattr(module, validation_ref['name'])
                            except (ImportError, AttributeError):
                                logger.warning(f"Could not resolve validation function {validation_key}")
                    else:
                        validation = validation_ref
                
                # Resolve outdated_check function
                outdated_check_ref = process_def.get('outdated_check_ref') or process_def.get('outdated_check')
                outdated_check = None
                if outdated_check_ref:
                    if isinstance(outdated_check_ref, dict):
                        outdated_check_key = f"{outdated_check_ref.get('module')}.{outdated_check_ref.get('name')}"
                        outdated_check = func_registry.get(outdated_check_key) or func_registry.get(outdated_check_ref.get('name'))
                        if not outdated_check:
                            try:
                                import importlib
                                module = importlib.import_module(outdated_check_ref['module'])
                                outdated_check = getattr(module, outdated_check_ref['name'])
                            except (ImportError, AttributeError):
                                logger.warning(f"Could not resolve outdated_check function {outdated_check_key}")
                    else:
                        outdated_check = outdated_check_ref
                
                # Get trigger from metadata or process_def
                metadata = process_def.get('metadata', {})
                trigger = metadata.get('trigger') or process_def.get('trigger')
                if trigger:
                    metadata['trigger'] = trigger
                
                # Build resolved process definition
                resolved_processes[process_name] = {
                    'func': func,
                    'dependencies': process_def.get('dependencies', []),
                    'cache_key': process_def.get('cache_key'),
                    'cache_ttl': process_def.get('cache_ttl'),
                    'validation': validation,
                    'outdated_check': outdated_check,
                    'required': process_def.get('required', True),
                    'metadata': metadata,
                    'trigger': trigger
                }
            
            resolved_tree[tree_name] = resolved_processes
        
        return resolved_tree
    
    @staticmethod
    def execute_tree(
        tree_name: str,
        context: Dict[str, Any] = None,
        func_registry: Dict[str, Callable] = None,
        sync_check_func: Callable = None,
        only_run_out_of_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a stored process tree by name.
        
        Args:
            tree_name: Name of the stored process tree
            context: Optional context dict
            func_registry: Dict mapping function references to actual callable functions
            sync_check_func: Optional sync check function
            only_run_out_of_sync: If True, only run out-of-sync processes
        
        Returns:
            Dict with execution results
        """
        instance = ProcessTreeManager.create_instance(tree_name, func_registry)
        
        if sync_check_func:
            return instance.execute_with_sync_check(
                tree_name,
                sync_check_func=sync_check_func,
                context=context or {},
                only_run_out_of_sync=only_run_out_of_sync
            )
        else:
            return instance.execute_tree(tree_name, context=context or {})
    
    @staticmethod
    def execute_with_dependents(
        tree_name: str,
        context: Dict[str, Any] = None,
        func_registry: Dict[str, Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute a process tree and all its dependent trees sequentially.
        
        Args:
            tree_name: Name of the stored process tree
            context: Optional context dict
            func_registry: Dict mapping function references to actual callable functions
        
        Returns:
            Dict with execution results for all trees
        """
        tree = ProcessTreeManager.get_tree(tree_name)
        if not tree:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        results = {
            'main_tree': tree_name,
            'trees_executed': [],
            'results': {}
        }
        
        # Execute main tree
        main_result = ProcessTreeManager.execute_tree(tree_name, context, func_registry)
        results['results'][tree_name] = main_result
        results['trees_executed'].append(tree_name)
        
        # Execute dependent trees sequentially
        for dependent_tree in tree.dependent_trees.filter(enabled=True):
            try:
                dep_result = ProcessTreeManager.execute_tree(
                    dependent_tree.name,
                    context,
                    func_registry
                )
                results['results'][dependent_tree.name] = dep_result
                results['trees_executed'].append(dependent_tree.name)
            except Exception as e:
                logger.error(f"Error executing dependent tree '{dependent_tree.name}': {e}")
                results['results'][dependent_tree.name] = {'success': False, 'error': str(e)}
        
        results['success'] = all(
            r.get('success', False) if isinstance(r, dict) else False
            for r in results['results'].values()
        )
        
        return results
    
    @staticmethod
    def execute_with_siblings(
        tree_name: str,
        context: Dict[str, Any] = None,
        func_registry: Dict[str, Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute a process tree and all its sibling trees in parallel (async).
        
        Note: This is a simplified version - in production you'd use actual async execution.
        
        Args:
            tree_name: Name of the stored process tree
            context: Optional context dict
            func_registry: Dict mapping function references to actual callable functions
        
        Returns:
            Dict with execution results for all trees
        """
        tree = ProcessTreeManager.get_tree(tree_name)
        if not tree:
            raise ValueError(f"Process tree '{tree_name}' not found")
        
        results = {
            'main_tree': tree_name,
            'sibling_trees': [],
            'results': {}
        }
        
        # Collect all sibling trees (including main tree)
        trees_to_execute = [tree]
        trees_to_execute.extend(tree.sibling_trees.filter(enabled=True))
        
        # Execute all trees (in production, this would be async)
        for tree_obj in trees_to_execute:
            try:
                tree_result = ProcessTreeManager.execute_tree(
                    tree_obj.name,
                    context,
                    func_registry
                )
                results['results'][tree_obj.name] = tree_result
                if tree_obj.name != tree_name:
                    results['sibling_trees'].append(tree_obj.name)
            except Exception as e:
                logger.error(f"Error executing sibling tree '{tree_obj.name}': {e}")
                results['results'][tree_obj.name] = {'success': False, 'error': str(e)}
        
        results['success'] = all(
            r.get('success', False) if isinstance(r, dict) else False
            for r in results['results'].values()
        )
        
        return results


class MethodHelper:
    """Helper class to provide method introspection and help."""
    
    def __init__(self, method, method_name: str, instance):
        self.method = method
        self.method_name = method_name
        self.instance = instance
    
    def __call__(self, *args, **kwargs):
        """Call the original method."""
        # The method is already bound to the instance, so call it directly
        return self.method(*args, **kwargs)
    
    def help(self):
        """Show help for this method."""
        sig = inspect.signature(self.method)
        doc = inspect.getdoc(self.method)
        
        print("=" * 70)
        print(f"ProcessTreeInstance.{self.method_name}()")
        print("=" * 70)
        print(f"\nSignature:\n{self.method_name}{sig}\n")
        if doc:
            print("Documentation:")
            print(doc)
        print("=" * 70)
    
    @property
    def signature(self):
        """Get the method signature."""
        return str(inspect.signature(self.method))
    
    @property
    def parameters(self):
        """Get method parameters as a dict."""
        sig = inspect.signature(self.method)
        params = {}
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            params[name] = {
                'name': name,
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'annotation': param.annotation if param.annotation != inspect.Parameter.empty else None,
                'kind': str(param.kind),
                'required': param.default == inspect.Parameter.empty
            }
        return params
    
    def list_parameters(self):
        """List all parameters for this method."""
        params = self.parameters
        print(f"\nParameters for {self.method_name}():")
        print("-" * 70)
        for name, info in params.items():
            required = "REQUIRED" if info['required'] else "OPTIONAL"
            default = f" (default: {info['default']})" if info['default'] is not None else ""
            annotation = f" -> {info['annotation']}" if info['annotation'] else ""
            print(f"  {name}: {required}{default}{annotation}")
        print("-" * 70)


class ProcessTreeInstance:
    """
    Instance-based ProcessTree wrapper that allows incremental building,
    configuration, and passing around.
    
    This class wraps a ProcessTree model instance and provides a fluent interface
    for building and configuring process trees incrementally. You can:
    - Create an instance and add processes as you go
    - Pass the instance around to different parts of your code
    - Add validation functions and other configuration
    - Save to database when ready
    
    Example:
        tree = ProcessTreeInstance('my_tree', description='My workflow')
        tree.add_process('step1', func=my_func)
        tree.add_process('step2', func=my_func2, dependencies=['step1'])
        tree.add_validation('step1', validate_step1)
        tree.save()  # Save to database
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        cache_enabled: bool = True,
        tree_instance: Optional[ProcessTree] = None,
        overwrite: bool = False
    ):
        """
        Initialize a ProcessTreeInstance.
        
        Args:
            name: Unique name for the process tree
            description: Description of what this process tree does
            cache_enabled: Whether to enable caching
            tree_instance: Optional existing ProcessTree model instance to wrap
            overwrite: If True, allow overwriting existing tree with same name (default: False)
        """
        self.name = name
        self.description = description
        self.cache_enabled = cache_enabled
        self.overwrite = overwrite
        
        # Store processes and configuration in memory
        self.processes: Dict[str, Dict[str, Any]] = {}
        self.response_variables: Dict[str, Dict[str, Any]] = {}
        self.validations: Dict[str, Callable] = {}
        self.func_registry: Dict[str, Callable] = {}
        
        # Optional: wrap an existing ProcessTree model instance
        self._tree_model: Optional[ProcessTree] = tree_instance
        
        # If wrapping an existing instance, load its data
        if tree_instance:
            self._load_from_model(tree_instance)
        elif not overwrite:
            # Check if tree with same name already exists
            if ProcessTree.objects.filter(name=name).exists():
                existing_tree = ProcessTree.objects.get(name=name)
                raise ValueError(
                    f"ProcessTree with name '{name}' already exists (ID: {existing_tree.id}). "
                    f"Set overwrite=True to overwrite it, or use load('{name}') to load the existing tree."
                )
        
        # Wrap methods with helper for introspection
        # Create MethodHelper instances that will wrap the methods
        self.add_process = MethodHelper(self._add_process_impl, 'add_process', self)
        self.add_validation = MethodHelper(self._add_validation_impl, 'add_validation', self)
        self.add_function = MethodHelper(self._add_function_impl, 'add_function', self)
    
    def _load_from_model(self, tree_model: ProcessTree):
        """Load data from an existing ProcessTree model instance."""
        self.name = tree_model.name
        self.description = tree_model.description
        self.cache_enabled = tree_model.cache_enabled
        
        # Load process tree data
        tree_data = tree_model.get_process_tree_dict()
        if tree_data and self.name in tree_data:
            self.processes = tree_data[self.name].copy()
        
        # Load response variables
        self.response_variables = tree_model.get_response_variables_dict()
        if self.name in self.response_variables:
            self.response_variables = self.response_variables[self.name]
    
    def _add_process_impl(
        self,
        process_name: str,
        func: Callable,
        dependencies: List[str] = None,
        cache_key: str = None,
        cache_ttl: int = None,
        validation: Callable = None,
        required: bool = True,
        metadata: Dict[str, Any] = None,
        response_vars: Dict[str, Dict[str, Any]] = None,
        outdated_check: Callable = None,
        trigger: Optional[str] = None  # Trigger name or ID
    ) -> 'ProcessTreeInstance':
        """
        Add a process to the tree.
        
        Args:
            process_name: Name of the process
            func: Function to execute
            dependencies: List of process names this depends on
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL in seconds
            validation: Optional validation function
            required: Whether process is required (default True)
            metadata: Optional metadata dict
            response_vars: Optional response variable definitions for this process
            outdated_check: Optional function that checks if data is outdated.
                          Should return True if data is outdated (process should run),
                          False if data is up-to-date (process should skip).
                          Function signature: outdated_check(**context) -> bool
            trigger: Optional trigger name or ID. If provided, the trigger's should_trigger()
                    method will be called to determine if the process should run.
                    Can be used instead of or in addition to outdated_check.
        
        Returns:
            self (for method chaining)
        """
        if dependencies is None:
            dependencies = []
        if metadata is None:
            metadata = {}
        
        self.processes[process_name] = {
            'func': func,
            'dependencies': dependencies,
            'cache_key': cache_key,
            'cache_ttl': cache_ttl,
            'validation': validation,
            'required': required,
            'metadata': metadata,
            'outdated_check': outdated_check,
            'trigger': trigger  # Trigger name or ID
        }
        
        # Store function in registry for later execution
        self.func_registry[process_name] = func
        
        # Store validation separately if provided
        if validation:
            self.validations[process_name] = validation
        
        # Store response variables if provided
        if response_vars:
            self.response_variables[process_name] = response_vars
        
        return self
    
    def _add_validation_impl(self, process_name: str, validation_func: Callable) -> 'ProcessTreeInstance':
        """
        Add or update a validation function for a process.
        
        Args:
            process_name: Name of the process to validate
            validation_func: Validation function to call
        
        Returns:
            self (for method chaining)
        """
        if process_name not in self.processes:
            raise ValueError(f"Process '{process_name}' not found. Add the process first.")
        
        self.validations[process_name] = validation_func
        self.processes[process_name]['validation'] = validation_func
        return self
    
    def _add_function_impl(self, name: str, func: Callable) -> 'ProcessTreeInstance':
        """
        Add a function to the function registry.
        Useful for adding functions that will be used by processes.
        
        Args:
            name: Name/key for the function
            func: Function to register
        
        Returns:
            self (for method chaining)
        """
        self.func_registry[name] = func
        return self
    
    def set_description(self, description: str) -> 'ProcessTreeInstance':
        """Set the description."""
        self.description = description
        return self
    
    def set_cache_enabled(self, enabled: bool) -> 'ProcessTreeInstance':
        """Enable or disable caching."""
        self.cache_enabled = enabled
        return self
    
    def get_process(self, process_name: str) -> Optional[Dict[str, Any]]:
        """Get a process definition by name."""
        return self.processes.get(process_name)
    
    def get_validation(self, process_name: str) -> Optional[Callable]:
        """Get validation function for a process."""
        return self.validations.get(process_name)
    
    def has_process(self, process_name: str) -> bool:
        """Check if a process exists."""
        return process_name in self.processes
    
    def remove_process(self, process_name: str) -> 'ProcessTreeInstance':
        """Remove a process from the tree."""
        if process_name in self.processes:
            del self.processes[process_name]
        if process_name in self.validations:
            del self.validations[process_name]
        if process_name in self.func_registry:
            del self.func_registry[process_name]
        if process_name in self.response_variables:
            del self.response_variables[process_name]
        return self
    
    def _get_function_ref(self, func: Callable) -> Dict[str, str]:
        """Get function reference for storage."""
        if func is None:
            return None
        if callable(func):
            return {
                'module': func.__module__ if hasattr(func, '__module__') else None,
                'name': func.__name__ if hasattr(func, '__name__') else str(func)
            }
        return func
    
    def save(self) -> ProcessTree:
        """
        Save the process tree to the database.
        
        Returns:
            ProcessTree model instance
        
        Raises:
            ValueError: If tree with same name exists and overwrite=False
        """
        # Check if tree exists and overwrite is False
        if not self.overwrite and not self._tree_model:
            if ProcessTree.objects.filter(name=self.name).exists():
                existing_tree = ProcessTree.objects.get(name=self.name)
                raise ValueError(
                    f"ProcessTree with name '{self.name}' already exists (ID: {existing_tree.id}). "
                    f"Set overwrite=True when creating ProcessTreeInstance to overwrite it, "
                    f"or use load('{self.name}') to load the existing tree."
                )
        
        process_tree_data = {}
        
        for process_name, process_def in self.processes.items():
            # Store function reference
            func = process_def['func']
            func_ref = self._get_function_ref(func)
            validation_ref = self._get_function_ref(process_def.get('validation'))
            
            outdated_check_ref = self._get_function_ref(process_def.get('outdated_check'))
            trigger = process_def.get('trigger')
            
            metadata = process_def.get('metadata', {})
            if trigger:
                metadata['trigger'] = trigger
            
            process_tree_data[process_name] = {
                'func_ref': func_ref,
                'dependencies': process_def['dependencies'],
                'cache_key': process_def.get('cache_key'),
                'cache_ttl': process_def.get('cache_ttl'),
                'validation_ref': validation_ref,
                'outdated_check_ref': outdated_check_ref,
                'required': process_def.get('required', True),
                'metadata': metadata
            }
        
        tree, created = ProcessTree.objects.update_or_create(
            name=self.name,
            defaults={
                'description': self.description,
                'process_tree_data': {self.name: process_tree_data},
                'response_variables': {self.name: self.response_variables} if self.response_variables else {},
                'cache_enabled': self.cache_enabled
            }
        )
        
        self._tree_model = tree
        action = 'Updated' if not created and self.overwrite else ('Created' if created else 'Updated')
        logger.info(f"{action} process tree '{self.name}'")
        return tree
    
    def load(self, tree_name: str) -> 'ProcessTreeInstance':
        """
        Load an existing ProcessTree from the database.
        
        Args:
            tree_name: Name of the tree to load
        
        Returns:
            self
        """
        try:
            tree_model = ProcessTree.objects.get(name=tree_name)
            self._load_from_model(tree_model)
            self._tree_model = tree_model
            return self
        except ProcessTree.DoesNotExist:
            raise ValueError(f"Process tree '{tree_name}' not found")
    
    def execute(
        self,
        context: Dict[str, Any] = None,
        sync_check_func: Callable = None,
        only_run_out_of_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Execute this process tree instance.
        
        Args:
            context: Optional context dict
            sync_check_func: Optional sync check function
            only_run_out_of_sync: If True, only run out-of-sync processes
        
        Returns:
            Dict with execution results
        """
        # First ensure we have a saved tree
        if not self._tree_model:
            self.save()
        
        # Use ProcessTreeManager to execute
        if sync_check_func:
            return ProcessTreeManager.execute_tree(
                self.name,
                context=context or {},
                func_registry=self.func_registry,
                sync_check_func=sync_check_func,
                only_run_out_of_sync=only_run_out_of_sync
            )
        else:
            return ProcessTreeManager.execute_tree(
                self.name,
                context=context or {},
                func_registry=self.func_registry
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the instance to a dictionary representation."""
        return {
            'name': self.name,
            'description': self.description,
            'cache_enabled': self.cache_enabled,
            'processes': {
                name: {
                    'dependencies': proc['dependencies'],
                    'cache_key': proc.get('cache_key'),
                    'cache_ttl': proc.get('cache_ttl'),
                    'required': proc.get('required', True),
                    'metadata': proc.get('metadata', {}),
                    'has_validation': proc.get('validation') is not None
                }
                for name, proc in self.processes.items()
            },
            'response_variables': self.response_variables,
            'has_validations': len(self.validations) > 0
        }
    
    def create_command(self, command_name: str = None, output_path: str = None) -> str:
        """
        Create a Django management command file for running this process tree.
        
        Args:
            command_name: Name for the command (defaults to tree name with underscores)
            output_path: Path where to write the command file (defaults to management/commands/)
        
        Returns:
            Path to the created command file
        """
        import os
        from pathlib import Path
        
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        # Generate command name
        if not command_name:
            command_name = self.name.lower().replace(' ', '_').replace('-', '_')
        
        # Determine output path
        if not output_path:
            # Default: apps/xero/xero_sync/management/commands/
            current_file = Path(__file__).resolve()
            # From: apps/xero/xero_sync/process_manager/tree_builder.py
            # To: apps/xero/xero_sync/management/commands/
            output_path = current_file.parent.parent / 'management' / 'commands'
            output_path.mkdir(parents=True, exist_ok=True)
        
        output_path = Path(output_path)
        command_file = output_path / f'{command_name}.py'
        
        # Generate command code
        command_code = f'''from django.core.management.base import BaseCommand
from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeManager


class Command(BaseCommand):
    help = 'Execute process tree: {self.name}'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--context',
            type=str,
            help='JSON string with context variables (e.g., {{"tenant_id": "123"}})',
        )
    
    def handle(self, *args, **options):
        # Import here to avoid circular imports
        from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeManager
        import json
        
        # Parse context if provided
        context = {{}}
        if options.get('context'):
            try:
                context = json.loads(options['context'])
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR('Invalid JSON in --context argument'))
                return
        
        # Execute the process tree
        try:
            results = ProcessTreeManager.execute_tree(
                '{self.name}',
                context=context,
                func_registry={{}}  # Functions should be registered in ProcessTreeInstance
            )
            
            if results.get('success'):
                self.stdout.write(self.style.SUCCESS(f'Process tree "{self.name}" executed successfully'))
                self.stdout.write(f'Results: {{results.get("results", {{}})}}')
            else:
                self.stdout.write(self.style.ERROR(f'Process tree "{self.name}" execution failed'))
                self.stdout.write(f'Errors: {{results.get("errors", [])}}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error executing process tree: {{str(e)}}'))
            import traceback
            self.stdout.write(traceback.format_exc())
'''
        
        # Write command file
        with open(command_file, 'w') as f:
            f.write(command_code)
        
        return str(command_file)
    
    def register_schedule(
        self,
        interval_minutes: int = 60,
        start_time: datetime.time = None,
        enabled: bool = True,
        context: Dict[str, Any] = None
    ):
        """
        Register this process tree with the task scheduler.
        
        Args:
            interval_minutes: Minutes between executions (default: 60)
            start_time: Preferred start time (default: midnight)
            enabled: Whether scheduling is enabled (default: True)
            context: Default context to pass to executions (default: empty dict)
        
        Returns:
            ProcessTreeSchedule instance
        """
        from apps.xero.xero_sync.models import ProcessTreeSchedule
        
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        # Get or create schedule
        schedule, created = ProcessTreeSchedule.objects.get_or_create(
            process_tree=self._tree_model,
            defaults={
                'enabled': enabled,
                'interval_minutes': interval_minutes,
                'start_time': start_time or datetime.time(0, 0),
                'context': context or {}
            }
        )
        
        if not created:
            # Update existing schedule
            schedule.enabled = enabled
            schedule.interval_minutes = interval_minutes
            if start_time:
                schedule.start_time = start_time
            if context is not None:
                schedule.context = context
            schedule.save()
        
        # Update next run time
        schedule.update_next_run_time()
        
        return schedule
    
    def create_trigger(
        self,
        name: str,
        trigger_type: str = 'condition',
        configuration: Dict[str, Any] = None,
        xero_last_update_id: Optional[int] = None,
        enabled: bool = True,
        description: str = ''
    ):
        """
        Create a trigger for this process tree.
        
        Args:
            name: Unique name for the trigger
            trigger_type: Type of trigger ('condition', 'schedule', 'event', 'custom', 'outdated_check')
            configuration: Trigger configuration dict
            xero_last_update_id: Optional XeroLastUpdate ID for outdated_check triggers
            enabled: Whether trigger is enabled (default: True)
            description: Description of the trigger
        
        Returns:
            Trigger instance
        """
        from apps.xero.xero_sync.models import Trigger, XeroLastUpdate
        
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        # Get XeroLastUpdate if provided
        xero_last_update = None
        if xero_last_update_id:
            try:
                xero_last_update = XeroLastUpdate.objects.get(id=xero_last_update_id)
            except XeroLastUpdate.DoesNotExist:
                raise ValueError(f"XeroLastUpdate with ID {xero_last_update_id} not found")
        
        # Create trigger
        trigger, created = Trigger.objects.get_or_create(
            name=name,
            defaults={
                'trigger_type': trigger_type,
                'enabled': enabled,
                'description': description,
                'configuration': configuration or {},
                'xero_last_update': xero_last_update,
                'process_tree': self._tree_model
            }
        )
        
        if not created:
            # Update existing trigger
            trigger.trigger_type = trigger_type
            trigger.enabled = enabled
            trigger.description = description
            if configuration is not None:
                trigger.configuration = configuration
            if xero_last_update:
                trigger.xero_last_update = xero_last_update
            trigger.process_tree = self._tree_model
            trigger.save()
        
        return trigger
    
    def subscribe_to_trigger(self, trigger_name: str):
        """
        Subscribe this process tree to a trigger.
        When the trigger fires, this tree will be executed.
        
        Args:
            trigger_name: Name of the trigger to subscribe to
        
        Returns:
            self (for method chaining)
        """
        from apps.xero.xero_sync.models import Trigger
        
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        try:
            trigger = Trigger.objects.get(name=trigger_name)
            self._tree_model.trigger = trigger
            self._tree_model.save(update_fields=['trigger'])
            logger.info(f"Subscribed process tree '{self.name}' to trigger '{trigger_name}'")
            return self
        except Trigger.DoesNotExist:
            raise ValueError(f"Trigger '{trigger_name}' not found")
    
    def unsubscribe_from_trigger(self):
        """
        Unsubscribe this process tree from its current trigger.
        
        Returns:
            self (for method chaining)
        """
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        if self._tree_model.trigger:
            trigger_name = self._tree_model.trigger.name
            self._tree_model.trigger = None
            self._tree_model.save(update_fields=['trigger'])
            logger.info(f"Unsubscribed process tree '{self.name}' from trigger '{trigger_name}'")
        
        return self
    
    def add_trigger_to_process(
        self,
        process_name: str,
        trigger_name: str
    ):
        """
        Add a trigger to a specific process.
        
        Args:
            process_name: Name of the process
            trigger_name: Name of the trigger to use
        
        Returns:
            self (for method chaining)
        """
        if process_name not in self.processes:
            raise ValueError(f"Process '{process_name}' not found")
        
        self.processes[process_name]['trigger'] = trigger_name
        return self
    
    def create_task_function(self):
        """
        Create a task function that can be used with APScheduler.
        
        Returns:
            Callable function that executes this process tree
        """
        # Ensure tree is saved
        if not self._tree_model:
            self.save()
        
        def task_function():
            """Task function for scheduler."""
            from apps.xero.xero_sync.models import ProcessTreeSchedule
            from apps.xero.xero_sync.process_manager.tree_builder import ProcessTreeManager
            import time
            import logging
            
            logger = logging.getLogger(__name__)
            
            try:
                # Get schedule
                schedule = ProcessTreeSchedule.objects.get(process_tree__name=self.name)
                
                # Check if should run
                if not schedule.should_run():
                    return
                
                logger.info(f"Starting scheduled execution of process tree: {self.name}")
                start_time = time.time()
                
                # Execute tree
                results = ProcessTreeManager.execute_tree(
                    self.name,
                    context=schedule.context or {},
                    func_registry=self.func_registry
                )
                
                duration = time.time() - start_time
                
                # Update schedule
                schedule.last_run = timezone.now()
                schedule.update_next_run_time()
                
                if results.get('success'):
                    logger.info(f"Completed scheduled execution of '{self.name}' in {duration:.2f} seconds")
                else:
                    logger.error(f"Scheduled execution of '{self.name}' failed: {results.get('errors', [])}")
                    
            except ProcessTreeSchedule.DoesNotExist:
                logger.warning(f"No schedule found for process tree: {self.name}")
            except Exception as e:
                logger.error(f"Error in scheduled task for '{self.name}': {str(e)}", exc_info=True)
        
        # Set function name for better logging
        task_function.__name__ = f'run_process_tree_{self.name}'
        task_function.__doc__ = f'Execute process tree: {self.name}'
        
        return task_function
    
    @staticmethod
    def show_add_process_help():
        """Print help for add_process method."""
        method = ProcessTreeInstance.add_process
        sig = inspect.signature(method)
        doc = inspect.getdoc(method)
        
        print("=" * 70)
        print("ProcessTreeInstance.add_process()")
        print("=" * 70)
        print(f"\nSignature:\n{method.__name__}{sig}\n")
        if doc:
            print("Documentation:")
            print(doc)
        print("\n" + "=" * 70)
        print("\nExample:")
        print("  tree.add_process(")
        print("      'process_name',")
        print("      func=my_function,")
        print("      dependencies=['dep1', 'dep2'],  # Optional")
        print("      cache_key='cache_key',          # Optional")
        print("      cache_ttl=3600,                 # Optional")
        print("      validation=validate_func,       # Optional")
        print("      required=True,                   # Optional, default True")
        print("      metadata={'key': 'value'},       # Optional")
        print("      response_vars={...}             # Optional")
        print("  )")
        print("=" * 70)
    
    @staticmethod
    def show_add_validation_help():
        """Print help for add_validation method."""
        method = ProcessTreeInstance.add_validation
        sig = inspect.signature(method)
        doc = inspect.getdoc(method)
        
        print("=" * 70)
        print("ProcessTreeInstance.add_validation()")
        print("=" * 70)
        print(f"\nSignature:\n{method.__name__}{sig}\n")
        if doc:
            print("Documentation:")
            print(doc)
        print("\n" + "=" * 70)
        print("\nExample:")
        print("  def validate_result(result):")
        print("      return result.get('status') == 'success'")
        print("  ")
        print("  tree.add_validation('process_name', validate_result)")
        print("=" * 70)
    
    @staticmethod
    def show_add_function_help():
        """Print help for add_function method."""
        method = ProcessTreeInstance.add_function
        sig = inspect.signature(method)
        doc = inspect.getdoc(method)
        
        print("=" * 70)
        print("ProcessTreeInstance.add_function()")
        print("=" * 70)
        print(f"\nSignature:\n{method.__name__}{sig}\n")
        if doc:
            print("Documentation:")
            print(doc)
        print("\n" + "=" * 70)
        print("\nExample:")
        print("  tree.add_function('my_func_name', my_function)")
        print("=" * 70)
    
    @staticmethod
    def show_all_methods():
        """Print all available methods and their signatures."""
        print("=" * 70)
        print("ProcessTreeInstance - Available Methods")
        print("=" * 70)
        
        methods = [
            ('add_process', ProcessTreeInstance.add_process),
            ('add_validation', ProcessTreeInstance.add_validation),
            ('add_function', ProcessTreeInstance.add_function),
            ('set_description', ProcessTreeInstance.set_description),
            ('set_cache_enabled', ProcessTreeInstance.set_cache_enabled),
            ('get_process', ProcessTreeInstance.get_process),
            ('get_validation', ProcessTreeInstance.get_validation),
            ('has_process', ProcessTreeInstance.has_process),
            ('remove_process', ProcessTreeInstance.remove_process),
            ('save', ProcessTreeInstance.save),
            ('load', ProcessTreeInstance.load),
            ('execute', ProcessTreeInstance.execute),
            ('to_dict', ProcessTreeInstance.to_dict),
        ]
        
        for name, method in methods:
            sig = inspect.signature(method)
            doc = inspect.getdoc(method)
            print(f"\n{name}{sig}")
            if doc:
                # Print first line of docstring
                first_line = doc.split('\n')[0] if doc else ""
                print(f"  {first_line}")
        
        print("\n" + "=" * 70)
        print("\nFor detailed help on a specific method:")
        print("  ProcessTreeInstance.show_add_process_help()")
        print("  ProcessTreeInstance.show_add_validation_help()")
        print("  ProcessTreeInstance.show_add_function_help()")
        print("=" * 70)
    
    def help(self, method_name: str = None):
        """
        Show help for a specific method or all methods.
        
        Args:
            method_name: Name of method to show help for (e.g., 'add_process')
                        If None, shows all methods
        """
        if method_name == 'add_process' or method_name is None:
            self.show_add_process_help()
        if method_name == 'add_validation' or method_name is None:
            if method_name:
                self.show_add_validation_help()
        if method_name == 'add_function' or method_name is None:
            if method_name:
                self.show_add_function_help()
        if method_name is None:
            self.show_all_methods()
        elif method_name not in ['add_process', 'add_validation', 'add_function']:
            print(f"Unknown method: {method_name}")
            print("Available methods: add_process, add_validation, add_function")
            self.show_all_methods()
    
    def __repr__(self) -> str:
        return f"ProcessTreeInstance(name='{self.name}', processes={len(self.processes)}, validations={len(self.validations)})"

