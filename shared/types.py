"""
Shared type definitions for Comfy Gimpy Studio.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskInfo:
    """Information about a task."""
    id: str
    operation: str
    state: str
    created_at: datetime
    parameters: Dict[str, Any]
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class QueueStats:
    """Queue statistics."""
    size: int
    max_size: int
    pending_count: int
    running_count: int
    completed_count: int
    failed_count: int
    utilization_percent: float


@dataclass
class SystemHealth:
    """System health information."""
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    memory_usage_percent: float
    cpu_usage_percent: float
    active_tasks: int
    queue_size: int
    last_error: Optional[str] = None


@dataclass
class OperationConfig:
    """Configuration for an operation."""
    name: str
    description: str
    parameters: Dict[str, Any]
    timeout_seconds: Optional[int] = None
    max_retries: int = 3
    priority: str = "normal"


@dataclass
class WorkflowStep:
    """A step in a workflow."""
    operation: str
    parameters: Dict[str, Any]
    depends_on: Optional[List[str]] = None
    timeout_seconds: Optional[int] = None


@dataclass
class Workflow:
    """A workflow definition."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: datetime
    metadata: Dict[str, Any]


# Type aliases
TaskId = str
OperationName = str
PriorityLevel = str  # "low", "normal", "high", "urgent"
TaskState = str  # "queued", "running", "completed", "failed", "cancelled", "timeout"


# Marketplace Pack Types
@dataclass
class PackManifest:
    """Pack manifest structure."""
    id: str
    type: str  # "template", "style", "workflow", "model"
    name: str
    version: str
    created_at: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    previews: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    license: str
    author: str
    description: str
    tags: List[str]
    checksums: Dict[str, str]


@dataclass
class PackInfo:
    """Pack information from registry."""
    id: str
    type: str
    name: str
    version: str
    installed_at: str
    manifest: PackManifest
    status: str


@dataclass
class PackDependency:
    """Pack dependency information."""
    name: str
    version: str
    type: Optional[str] = None
    required: bool = True


@dataclass
class PackPreview:
    """Pack preview information."""
    filename: str
    path: str
    checksum: str
    size: int


@dataclass
class PackInstallationResult:
    """Result of pack installation."""
    success: bool
    pack_id: Optional[str] = None
    install_path: Optional[str] = None
    manifest: Optional[PackManifest] = None
    installed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PackUpdateResult:
    """Result of pack update."""
    success: bool
    pack_id: str
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


# Additional type aliases for packs
PackId = str
PackType = str  # "template", "style", "workflow", "model"
PackVersion = str
PackStatus = str  # "active", "inactive"


# Fusion Engine Types
@dataclass
class FusionOptions:
    """Options for fusion operations."""
    lora_weights: Optional[Dict[str, float]] = None
    style_mix_ratios: Optional[Dict[str, float]] = None
    brand_kit_id: Optional[str] = None
    variant_count: int = 1
    randomness_seed: Optional[int] = None
    generate_previews: bool = True
    output_format: str = "png"
    quality: int = 95


@dataclass
class FusionResult:
    """Result of a fusion operation."""
    task_id: str
    variants: List[Dict[str, Any]]
    preview_urls: Optional[List[str]] = None
    brand_kit_applied: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class BrandKit:
    """A brand kit definition."""
    id: str
    name: str
    description: str
    version: str
    colors: Dict[str, str]  # Color palette
    fonts: Dict[str, Any]   # Font specifications
    logos: Dict[str, str]   # Logo paths/URLs
    guidelines: Dict[str, Any]  # Brand guidelines
    assets: Dict[str, str]  # Additional brand assets
    metadata: Dict[str, Any]


@dataclass
class VariantParameters:
    """Parameters for variant generation."""
    prompt_variation_strength: float = 0.3
    style_noise_strength: float = 0.2
    composition_variation: float = 0.1
    color_temperature_shift: float = 0.05
    lighting_variation: float = 0.15


# Additional type aliases for fusion
FusionId = str
BrandKitId = str
VariantId = str
LoRAName = str


# Workflow Auto-Generation Types
@dataclass
class WorkflowTemplate:
    """Template for workflow generation."""
    id: str
    name: str
    description: str
    type: str  # "txt2img", "img2img", "inpainting", etc.
    version: str
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []


@dataclass
class WorkflowGraph:
    """ComfyUI workflow graph representation."""
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowBuildOptions:
    """Options for workflow building."""
    optimize: bool = True
    validate: bool = True
    cache_enabled: bool = True
    max_nodes: int = 100
    timeout: float = 30.0
    include_previews: bool = True
    style_strength: float = 1.0
    template_variation: str = "default"


@dataclass
class WorkflowBuildResult:
    """Result of workflow building."""
    success: bool
    workflow: Optional[WorkflowGraph] = None
    errors: List[str] = None
    warnings: List[str] = None
    build_time: float = 0.0
    node_count: int = 0
    cache_hit: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class WorkflowValidationResult:
    """Result of workflow validation."""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class WorkflowRule:
    """Rule for workflow generation."""
    id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowRuleContext:
    """Context for rule evaluation."""
    template: WorkflowTemplate
    style: Optional[Any] = None  # Forward reference to Style
    user_options: Dict[str, Any] = None
    environment: Dict[str, Any] = None

    def __post_init__(self):
        if self.user_options is None:
            self.user_options = {}
        if self.environment is None:
            self.environment = {}


@dataclass
class WorkflowRuleResult:
    """Result of rule evaluation."""
    rule_id: str
    matched: bool
    actions: List[Dict[str, Any]] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.metadata is None:
            self.metadata = {}


# Additional type aliases for workflow auto-generation
WorkflowTemplateId = str
WorkflowGraphId = str
WorkflowRuleId = str


# Phase 9 - Real ComfyUI Integration Types

@dataclass
class ExecutionResult:
    """Result of a ComfyUI workflow execution."""
    success: bool
    outputs: Dict[str, Any] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.outputs is None:
            self.outputs = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionStatus:
    """Status of an execution job."""
    job_id: str
    state: str  # "pending", "running", "completed", "failed", "cancelled"
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WorkflowData:
    """Data structure for workflow execution."""
    workflow_json: Dict[str, Any]
    template_id: Optional[str] = None
    style_id: Optional[str] = None
    node_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessedOutput:
    """Processed output from execution result."""
    key: str
    type: str  # "image", "video", "text", "generic"
    data: Any
    metadata: Dict[str, Any] = None
    file_path: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionMetrics:
    """Metrics for execution performance."""
    job_id: str
    execution_time: float
    queue_wait_time: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_memory_usage: float = 0.0
    network_io: int = 0
    disk_io: int = 0
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


@dataclass
class SystemResourceUsage:
    """System resource usage information."""
    cpu_percent: float
    memory_used_mb: float
    memory_total_mb: float
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


@dataclass
class ExecutionAlert:
    """Alert for execution issues."""
    alert_id: str
    level: str  # "info", "warning", "error", "critical"
    message: str
    job_id: Optional[str] = None
    timestamp: float = None
    resolved: bool = False
    resolution_time: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


@dataclass
class BatchExecutionResult:
    """Result of batch execution."""
    batch_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_execution_time: float
    average_execution_time: float
    success_rate: float
    job_results: List[ExecutionResult] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.job_results is None:
            self.job_results = []
        if self.metadata is None:
            self.metadata = {}


# Type aliases for execution system
ExecutionJobId = str
ComfyUIHost = str
ComfyUIPort = int
WorkflowExecutionId = str


# Phase 10 - Advanced Workflow Optimization Types

@dataclass
class OptimizationProfile:
    """Performance optimization profile for workflows."""
    workflow_hash: str
    execution_times: List[float] = None
    memory_usage: List[float] = None
    gpu_usage: List[float] = None
    success_rate: float = 1.0
    optimal_batch_size: int = 1
    recommended_concurrency: int = 1
    last_updated: datetime = None
    execution_count: int = 0

    def __post_init__(self):
        if self.execution_times is None:
            self.execution_times = []
        if self.memory_usage is None:
            self.memory_usage = []
        if self.gpu_usage is None:
            self.gpu_usage = []
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class ServerNode:
    """Represents a ComfyUI server node in distributed setup."""
    host: str
    port: int
    priority: int = 1
    max_concurrent_jobs: int = 4
    active_jobs: int = 0
    is_online: bool = True
    last_health_check: datetime = None
    performance_score: float = 1.0
    capabilities: Dict[str, Any] = None

    def __post_init__(self):
        if self.last_health_check is None:
            self.last_health_check = datetime.now()
        if self.capabilities is None:
            self.capabilities = {}


@dataclass
class DistributedJob:
    """Job distributed across multiple server nodes."""
    job_id: str
    workflow_data: Dict[str, Any]
    sub_jobs: List[Dict[str, Any]] = None
    coordinator_node: Optional[ServerNode] = None
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[ExecutionResult] = None

    def __post_init__(self):
        if self.sub_jobs is None:
            self.sub_jobs = []
        if self.results is None:
            self.results = []


@dataclass
class ResourceMetrics:
    """Real-time resource usage metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    gpu_utilization: float = 0.0
    disk_usage_percent: float = 0.0
    network_io: Dict[str, float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.network_io is None:
            self.network_io = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    action: str  # 'reduce_concurrency', 'pause_jobs', 'alert', 'optimize'


@dataclass
class OptimizationAction:
    """Optimization action to be taken."""
    action_type: str  # 'reduce_batch_size', 'increase_concurrency', 'enable_caching', etc.
    target_component: str
    parameters: Dict[str, Any] = None
    priority: int = 1
    timestamp: datetime = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class LoadBalancingStrategy:
    """Load balancing strategy configuration."""
    name: str
    weight_cpu: float = 1.0
    weight_memory: float = 1.0
    weight_gpu: float = 1.0
    weight_latency: float = 1.0
    priority_preference: bool = True


@dataclass
class NodeHealthStatus:
    """Health status of a server node."""
    node_id: str
    is_online: bool
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    system_load: Dict[str, float] = None

    def __post_init__(self):
        if self.system_load is None:
            self.system_load = {}


@dataclass
class CacheEntry:
    """Intelligent caching entry for workflow results."""
    cache_key: str
    result: ExecutionResult
    created_at: datetime = None
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = datetime.now()
        if self.metadata is None:
            self.metadata = {}


# Type aliases for optimization system
WorkflowHash = str
NodeId = str
OptimizationActionType = str
LoadBalancingStrategyName = str