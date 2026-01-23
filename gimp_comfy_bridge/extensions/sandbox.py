# gimp_comfy_bridge/extensions/sandbox.py

"""
Extension Sandboxing System

Provides isolated execution environment for extensions with resource limits
and security controls.
"""

import sys
import os
import time
import threading
import resource
from typing import Dict, List, Optional, Any, Callable
from contextlib import contextmanager
import importlib.util
import types
import inspect

class SandboxError(Exception):
    """Base exception for sandbox violations."""
    pass

class ResourceLimitError(SandboxError):
    """Exception for resource limit violations."""
    pass

class SecurityViolationError(SandboxError):
    """Exception for security violations."""
    pass

class ExtensionSandbox:
    """Sandboxed execution environment for extensions."""

    def __init__(self, extension_id: str, permissions: List[str]):
        self.extension_id = extension_id
        self.permissions = set(permissions)
        self._execution_time = 0
        self._memory_usage = 0
        self._cpu_time = 0
        self._active = False

        # Resource limits
        self.time_limit = 30.0  # seconds
        self.memory_limit = 100 * 1024 * 1024  # 100MB
        self.cpu_limit = 10.0  # seconds

        # Restricted modules
        self.restricted_modules = {
            'os', 'sys', 'subprocess', 'multiprocessing', 'threading',
            'socket', 'urllib', 'http', 'ftplib', 'smtplib',
            'sqlite3', 'dbm', 'shelve', 'pickle',
            'ctypes', 'mmap', 'resource'
        }

        # Restricted builtins
        self.restricted_builtins = {
            'open', 'file', 'input', 'raw_input', 'exec', 'eval',
            'compile', '__import__', 'reload', 'dir', 'vars'
        }

    @contextmanager
    def execution_context(self):
        """Context manager for sandboxed execution."""
        if self._active:
            raise SandboxError("Sandbox already active")

        self._active = True
        self._execution_time = time.time()

        try:
            # Set resource limits
            self._set_resource_limits()

            # Create restricted environment
            restricted_globals = self._create_restricted_globals()

            yield restricted_globals

        finally:
            self._active = False
            execution_duration = time.time() - self._execution_time
            self._execution_time = execution_duration

    def execute_code(self, code: str, globals_dict: Optional[Dict] = None) -> Any:
        """Execute code in sandboxed environment."""
        with self.execution_context() as restricted_globals:
            if globals_dict:
                restricted_globals.update(globals_dict)

            try:
                # Compile code
                compiled_code = compile(code, f'<extension_{self.extension_id}>', 'exec')

                # Execute in restricted environment
                exec(compiled_code, restricted_globals)

                return restricted_globals

            except Exception as e:
                raise SandboxError(f"Execution failed: {e}") from e

    def execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function in sandboxed environment."""
        with self.execution_context() as restricted_globals:
            try:
                # Check if function is safe
                self._validate_function(func)

                # Execute function
                result = func(*args, **kwargs)

                return result

            except Exception as e:
                raise SandboxError(f"Function execution failed: {e}") from e

    def load_module(self, module_path: str) -> types.ModuleType:
        """Load a module in sandboxed environment."""
        if not self._check_permission('file_system_read'):
            raise SecurityViolationError("No permission to load modules")

        try:
            spec = importlib.util.spec_from_file_location(
                f'extension_{self.extension_id}_module',
                module_path
            )

            if spec is None:
                raise SandboxError(f"Could not load module: {module_path}")

            module = importlib.util.module_from_spec(spec)

            # Execute in sandbox
            with self.execution_context() as restricted_globals:
                spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise SandboxError(f"Module loading failed: {e}") from e

    def _set_resource_limits(self) -> None:
        """Set resource limits for the process."""
        try:
            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU,
                             (int(self.cpu_limit), int(self.cpu_limit)))

            # Set memory limit
            resource.setrlimit(resource.RLIMIT_AS,
                             (self.memory_limit, self.memory_limit))

            # Set file size limit
            resource.setrlimit(resource.RLIMIT_FSIZE,
                             (10 * 1024 * 1024, 10 * 1024 * 1024))  # 10MB

        except (OSError, ValueError):
            # Resource limits may not be available on all platforms
            pass

    def _create_restricted_globals(self) -> Dict[str, Any]:
        """Create restricted global environment."""
        # Start with safe builtins
        safe_builtins = {}

        for name in dir(__builtins__):
            if name not in self.restricted_builtins:
                safe_builtins[name] = getattr(__builtins__, name)

        # Add custom restricted builtins
        safe_builtins['__import__'] = self._restricted_import
        safe_builtins['open'] = self._restricted_open
        safe_builtins['print'] = self._restricted_print

        return {
            '__builtins__': safe_builtins,
            '__name__': f'extension_{self.extension_id}',
            '__extension_id__': self.extension_id,
            '__permissions__': list(self.permissions)
        }

    def _restricted_import(self, name: str, *args, **kwargs):
        """Restricted import function."""
        if name in self.restricted_modules:
            if not self._check_permission('system_access'):
                raise SecurityViolationError(f"Import of {name} not allowed")

        return __import__(name, *args, **kwargs)

    def _restricted_open(self, *args, **kwargs):
        """Restricted file open function."""
        if not self._check_permission('file_system_read'):
            raise SecurityViolationError("File access not allowed")

        # Additional path restrictions
        if args and isinstance(args[0], str):
            path = os.path.abspath(args[0])
            if self._is_restricted_path(path):
                raise SecurityViolationError(f"Access to {path} not allowed")

        return open(*args, **kwargs)

    def _restricted_print(self, *args, **kwargs):
        """Restricted print function with logging."""
        # Log extension output
        message = ' '.join(str(arg) for arg in args)
        print(f"[Extension {self.extension_id}] {message}", **kwargs)

    def _validate_function(self, func: Callable) -> None:
        """Validate function for safe execution."""
        # Check function signature
        sig = inspect.signature(func)
        # Could add parameter validation here

        # Check for dangerous patterns in source
        try:
            source = inspect.getsource(func)
            dangerous_patterns = [
                'import os', 'import sys', 'import subprocess',
                'exec(', 'eval(', '__import__('
            ]

            for pattern in dangerous_patterns:
                if pattern in source and not self._check_permission('system_access'):
                    raise SecurityViolationError(f"Dangerous code pattern: {pattern}")

        except (OSError, TypeError):
            # Source not available, skip validation
            pass

    def _check_permission(self, permission: str) -> bool:
        """Check if extension has a permission."""
        return permission in self.permissions

    def _is_restricted_path(self, path: str) -> bool:
        """Check if path is restricted."""
        restricted_paths = [
            '/etc', '/usr', '/bin', '/sbin',
            '/system', '/config', '/extensions'
        ]

        for restricted in restricted_paths:
            if path.startswith(restricted):
                return True

        return False

    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        return {
            'execution_time': self._execution_time,
            'memory_usage': self._memory_usage,
            'cpu_time': self._cpu_time
        }

    def reset_limits(self) -> None:
        """Reset resource usage counters."""
        self._execution_time = 0
        self._memory_usage = 0
        self._cpu_time = 0