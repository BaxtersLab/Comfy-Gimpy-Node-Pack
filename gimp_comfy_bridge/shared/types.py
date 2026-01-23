"""
Type definitions for the bridge.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

@dataclass
class HistoryMetadata:
    """
    Metadata for a history step.
    """
    step: int
    timestamp: str
    workflow: str
    mode: str
    input_file: Optional[str]
    mask_file: Optional[str]
    output_file: str
    params_file: str
    notes: str

@dataclass
class WorkflowParams:
    """
    Parameters for workflow execution.
    """
    prompt: Optional[str]
    negative_prompt: Optional[str]
    width: Optional[int]
    height: Optional[int]
    strength: Optional[float]
    upscale_factor: Optional[float]
    model: Optional[str]
    loras: Optional[list]
    controlnet: Optional[list]

@dataclass
class TemplateMetadata:
    """
    Metadata for a template.
    """
    name: str
    category: str
    description: str
    required_workflow: str
    recommended_styles: List[str]
    tags: List[str]
    version: Optional[str] = None
    author: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None
    dependencies: Optional[Dict[str, Any]] = None

@dataclass
class TemplateInfo:
    """
    Basic information about a template.
    """
    category: str
    name: str
    path: Path
    metadata: Optional[TemplateMetadata] = None

@dataclass
class TemplateCategory:
    """
    Information about a template category.
    """
    name: str
    display_name: str
    description: str
    template_count: int = 0

@dataclass
class StyleMetadata:
    """
    Metadata for a style.
    """
    name: str
    category: str
    description: str
    tags: List[str]
    default_weight: float

@dataclass
class StyleInfo:
    """
    Basic information about a style.
    """
    name: str
    category: str
    path: Path
    metadata: Optional[StyleMetadata] = None
    has_preview: bool = False

@dataclass
class StyleCategory:
    """
    Information about a style category.
    """
    name: str
    display_name: str
    description: str
    style_count: int = 0


# Template Generation Types

@dataclass
class TemplateGenerationOptions:
    """
    Options for template generation.
    """
    category: str = "general"
    generate_variants: bool = True
    variant_count: int = 3
    style_references: Optional[List[str]] = None
    brand_kit_id: Optional[str] = None
    output_format: str = "xcf"
    include_previews: bool = True
    quality: int = 95


@dataclass
class TemplateGenerationRequest:
    """
    Request for template generation.
    """
    method: str  # "prompt", "image", "workflow", "enhancement"
    prompt: Optional[str] = None
    image_path: Optional[str] = None
    workflow_data: Optional[Dict[str, Any]] = None
    base_template: Optional[Dict[str, Any]] = None
    options: Optional[TemplateGenerationOptions] = None


@dataclass
class TemplateGenerationResult:
    """
    Result of template generation.
    """
    template: Dict[str, Any]
    variants: List[Dict[str, Any]]
    preview_urls: Optional[List[str]] = None
    saved_path: Optional[str] = None
    generation_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class TemplateLayoutElement:
    """
    Element in a template layout.
    """
    id: str
    type: str  # "text", "image", "shape", "background"
    position: Dict[str, float]  # x, y, width, height (normalized 0-1)
    properties: Dict[str, Any]
    layer_name: Optional[str] = None
    z_index: int = 0


@dataclass
class TemplateLayout:
    """
    Layout definition for a template.
    """
    elements: List[TemplateLayoutElement]
    canvas_size: Dict[str, int]  # width, height in pixels
    background_color: Optional[str] = None
    resolution: int = 300  # DPI
    color_mode: str = "RGB"


@dataclass
class TemplateVariant:
    """
    A variant of a generated template.
    """
    id: str
    name: str
    layout: TemplateLayout
    modifications: Dict[str, Any]  # What was changed from base
    preview_url: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class GeneratedTemplateMetadata:
    """
    Metadata for a generated template.
    """
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    generated_from: str  # "prompt", "image", "workflow", "enhancement"
    source_prompt: Optional[str] = None
    source_image: Optional[str] = None
    source_workflow: Optional[str] = None
    ai_enhanced: bool = True
    version: str = "1.0"
    created_at: str = ""
    author: str = "Comfy Gimpy Studio"


# Remote Execution Types

@dataclass
class RemoteNodeCapabilities:
    """
    Capabilities of a remote ComfyUI node.
    """
    vram_gb: float
    models: List[str]
    loras: List[str]
    workflows: List[str]
    supported_operations: List[str]
    max_batch_size: int = 1
    gpu_type: Optional[str] = None
    cuda_version: Optional[str] = None


@dataclass
class RemoteNodeStatus:
    """
    Status of a remote ComfyUI node.
    """
    id: str
    url: str
    status: str  # "online", "offline", "busy", "error"
    capabilities: Optional[RemoteNodeCapabilities] = None
    last_seen: Optional[str] = None
    response_time: float = 0.0
    error_count: int = 0
    uptime: float = 0.0
    total_requests: int = 0
    active_tasks: int = 0


@dataclass
class RemoteTaskRequest:
    """
    Request to execute a task on a remote node.
    """
    operation: str
    parameters: Dict[str, Any]
    priority: str = "normal"
    timeout_seconds: Optional[int] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RemoteTaskResult:
    """
    Result of a remote task execution.
    """
    task_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    node_id: Optional[str] = None


# Cloud Sync Types

@dataclass
class SyncConfig:
    """
    Configuration for cloud sync providers.
    """
    @dataclass
    class ProviderConfig:
        name: str
        type: str  # "local", "http", "s3", "dropbox", etc.
        settings: Dict[str, Any]
        enabled: bool = True

    providers: List[ProviderConfig] = None
    auto_sync: bool = True
    sync_interval_minutes: int = 60
    conflict_resolution: str = "newer_wins"
    encrypt_sync: bool = False
    excluded_patterns: List[str] = None

    def __post_init__(self):
        if self.providers is None:
            self.providers = []
        if self.excluded_patterns is None:
            self.excluded_patterns = [".git/**", "**/node_modules/**", "**/__pycache__/**", "**/*.tmp"]


@dataclass
class SyncItem:
    """
    Item in cloud storage for sync.
    """
    path: str
    size: int
    modified_time: str
    is_directory: bool
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SyncResult:
    """
    Result of a sync operation.
    """
    success: bool
    items_synced: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    errors: List[str] = None
    duration: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class SyncConflict:
    """
    A conflict detected during sync.
    """
    path: str
    local_info: Optional[SyncItem] = None
    remote_info: Optional[SyncItem] = None
    conflict_type: str = "modified_both"  # "modified_both", "deleted_locally", "deleted_remotely", "type_changed"
    resolution: Optional[str] = None


@dataclass
class SyncJob:
    """
    A sync job configuration.
    """
    job_id: str
    local_path: str
    remote_path: str
    provider_name: str
    direction: str = "bidirectional"  # "upload", "download", "bidirectional"
    exclude_patterns: List[str] = None
    conflict_resolution: str = "newer_wins"
    scheduled_time: Optional[str] = None
    status: str = "pending"
    result: Optional[SyncResult] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = []


# Brand Kit Types

@dataclass
class BrandKitInfo:
    """
    Basic information about a brand kit.
    """
    name: str
    description: str
    version: str
    path: str
    source: str  # 'local' or 'sync'
    tags: List[str]
    updated_at: str
    has_preview: bool = False
    color_count: int = 0
    style_count: int = 0
    logo_count: int = 0

@dataclass
class BrandKitSummary:
    """
    Summary information for brand kit listings.
    """
    total_kits: int
    local_kits: int
    sync_kits: int
    categories: Dict[str, int]  # tag -> count

@dataclass
class BrandKitApplication:
    """
    Information about brand kit application to content.
    """
    kit_name: str
    kit_version: str
    applied_at: str  # 'template', 'style', 'workflow', 'generation'
    applied_components: List[str]  # ['colors', 'fonts', 'styles', etc.]
    timestamp: str

@dataclass
class BrandKitValidationResult:
    """
    Result of brand kit validation.
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    kit_name: str
    validated_at: str