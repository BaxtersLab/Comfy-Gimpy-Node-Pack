"""
Comfy Gimpy Studio - Phase 9: Real ComfyUI Integration
Execution system for connecting fusion results to actual ComfyUI workflow execution.
"""

from .engine import (
    initialize_execution_engine,
    execute_workflow,
    execute_fusion_result,
    get_execution_monitor,
    ComfyUIClient,
    WebSocketMonitor,
    ExecutionJob,
    ExecutionOptions,
    WorkflowData
)

from .processor import (
    ResultProcessor,
    BatchProcessor,
    ProcessingOptions,
    ProcessedOutput
)

from .monitor import (
    ExecutionMonitor,
    PerformanceMetrics,
    SystemHealth,
    AnalyticsDashboard,
    ExecutionAlert
)

__all__ = [
    # Engine exports
    'initialize_execution_engine',
    'execute_workflow',
    'execute_fusion_result',
    'get_execution_monitor',
    'ComfyUIClient',
    'WebSocketMonitor',
    'ExecutionJob',
    'ExecutionOptions',
    'WorkflowData',

    # Processor exports
    'ResultProcessor',
    'BatchProcessor',
    'ProcessingOptions',
    'ProcessedOutput',

    # Monitor exports
    'ExecutionMonitor',
    'PerformanceMetrics',
    'SystemHealth',
    'AnalyticsDashboard',
    'ExecutionAlert'
]