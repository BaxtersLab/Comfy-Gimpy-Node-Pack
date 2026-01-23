# gimp_comfy_bridge/extensions/api.py

"""
Extension API

Provides the API that extensions use to interact with Comfy Gimpy Studio.
"""

from typing import Dict, List, Optional, Any, Callable, Union
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class ExtensionAPI:
    """API for extensions to interact with Comfy Gimpy Studio."""

    def __init__(self, extension_id: str, registry: 'ExtensionRegistry'):
        self.extension_id = extension_id
        self.registry = registry

    # UI Integration
    def register_ui_panel(self, panel_id: str, panel_class: type) -> None:
        """Register a UI panel."""
        logger.info(f"Extension {self.extension_id} registering UI panel: {panel_id}")
        # Implementation would integrate with GIMP UI system
        pass

    def inject_ui_element(self, location: str, element_id: str, element: Any) -> None:
        """Inject a UI element into the interface."""
        logger.info(f"Extension {self.extension_id} injecting UI element: {element_id} at {location}")
        # Implementation would integrate with GIMP UI system
        pass

    def add_menu_item(self, menu_path: str, item_id: str, callback: Callable) -> None:
        """Add a menu item."""
        logger.info(f"Extension {self.extension_id} adding menu item: {item_id}")
        # Implementation would integrate with GIMP menu system
        pass

    # Workflow Integration
    def register_workflow(self, workflow_id: str, workflow_def: Dict[str, Any]) -> None:
        """Register a workflow."""
        logger.info(f"Extension {self.extension_id} registering workflow: {workflow_id}")
        # Implementation would integrate with workflow system
        pass

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Any:
        """Execute a workflow."""
        logger.info(f"Extension {self.extension_id} executing workflow: {workflow_id}")
        # Implementation would integrate with workflow execution
        return None

    # Asset System Integration
    def register_asset_type(self, asset_type: str, handler_class: type) -> None:
        """Register a new asset type."""
        logger.info(f"Extension {self.extension_id} registering asset type: {asset_type}")
        # Implementation would integrate with asset system
        pass

    def add_asset(self, asset_data: Dict[str, Any]) -> str:
        """Add an asset to the library."""
        logger.info(f"Extension {self.extension_id} adding asset")
        # Implementation would integrate with asset library
        return "asset_id"

    def get_assets(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get assets from the library."""
        logger.info(f"Extension {self.extension_id} querying assets")
        # Implementation would integrate with asset library
        return []

    # Template System Integration
    def register_template_generator(self, generator_id: str, generator_func: Callable) -> None:
        """Register a template generator."""
        logger.info(f"Extension {self.extension_id} registering template generator: {generator_id}")
        # Implementation would integrate with template system
        pass

    def generate_template(self, generator_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a template."""
        logger.info(f"Extension {self.extension_id} generating template with {generator_id}")
        # Implementation would integrate with template generation
        return {}

    # Copywriting Integration
    def register_copywriting_module(self, module_id: str, module_class: type) -> None:
        """Register a copywriting module."""
        logger.info(f"Extension {self.extension_id} registering copywriting module: {module_id}")
        # Implementation would integrate with copywriting system
        pass

    def generate_copy(self, module_id: str, context: Dict[str, Any]) -> str:
        """Generate copy using a module."""
        logger.info(f"Extension {self.extension_id} generating copy with {module_id}")
        # Implementation would integrate with copywriting system
        return ""

    # Brand Kit Integration
    def register_brand_tool(self, tool_id: str, tool_class: type) -> None:
        """Register a brand kit tool."""
        logger.info(f"Extension {self.extension_id} registering brand tool: {tool_id}")
        # Implementation would integrate with brand kit system
        pass

    def apply_brand_tool(self, tool_id: str, brand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a brand tool."""
        logger.info(f"Extension {self.extension_id} applying brand tool: {tool_id}")
        # Implementation would integrate with brand kit system
        return {}

    # Layout Optimization Integration
    def register_layout_heuristic(self, heuristic_id: str, heuristic_func: Callable) -> None:
        """Register a layout optimization heuristic."""
        logger.info(f"Extension {self.extension_id} registering layout heuristic: {heuristic_id}")
        # Implementation would integrate with layout optimization
        pass

    def optimize_layout(self, heuristic_id: str, layout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply layout optimization."""
        logger.info(f"Extension {self.extension_id} optimizing layout with {heuristic_id}")
        # Implementation would integrate with layout optimization
        return layout_data

    # Event System
    def subscribe_event(self, event_type: str, callback: Callable) -> None:
        """Subscribe to an event."""
        logger.info(f"Extension {self.extension_id} subscribing to event: {event_type}")
        # Implementation would integrate with event system
        pass

    def publish_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish an event."""
        logger.info(f"Extension {self.extension_id} publishing event: {event_type}")
        # Implementation would integrate with event system
        pass

    # Configuration
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        logger.debug(f"Extension {self.extension_id} getting config: {key}")
        # Implementation would integrate with config system
        return default

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        logger.debug(f"Extension {self.extension_id} setting config: {key}")
        # Implementation would integrate with config system
        pass

    # File System (with permission checks)
    def read_file(self, path: str) -> str:
        """Read a file."""
        logger.debug(f"Extension {self.extension_id} reading file: {path}")
        # Implementation would check permissions and read file
        return ""

    def write_file(self, path: str, content: str) -> None:
        """Write a file."""
        logger.debug(f"Extension {self.extension_id} writing file: {path}")
        # Implementation would check permissions and write file
        pass

    # HTTP Requests (with permission checks)
    def http_request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make an HTTP request."""
        logger.debug(f"Extension {self.extension_id} making HTTP request: {method} {url}")
        # Implementation would check permissions and make request
        return {}

    # Logging
    def log(self, level: str, message: str, **kwargs) -> None:
        """Log a message."""
        logger.log(getattr(logging, level.upper(), logging.INFO),
                  f"Extension {self.extension_id}: {message}", **kwargs)

    # Utility Functions
    def show_notification(self, title: str, message: str, level: str = "info") -> None:
        """Show a notification to the user."""
        logger.info(f"Extension {self.extension_id} showing notification: {title}")
        # Implementation would show notification in UI
        pass

    def show_dialog(self, dialog_type: str, **kwargs) -> Any:
        """Show a dialog to the user."""
        logger.info(f"Extension {self.extension_id} showing dialog: {dialog_type}")
        # Implementation would show dialog in UI
        return None

    def get_user_input(self, prompt: str, input_type: str = "text") -> Any:
        """Get input from the user."""
        logger.info(f"Extension {self.extension_id} requesting user input: {prompt}")
        # Implementation would request input from UI
        return None

class ExtensionBase(ABC):
    """Base class for extensions."""

    def __init__(self, api: ExtensionAPI):
        self.api = api
        self.extension_id = api.extension_id

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the extension."""
        pass

    def cleanup(self) -> None:
        """Cleanup the extension."""
        pass

    def on_enable(self) -> None:
        """Called when extension is enabled."""
        pass

    def on_disable(self) -> None:
        """Called when extension is disabled."""
        pass

# Hook system for extensions
class ExtensionHooks:
    """Hook system for extensions."""

    def __init__(self, registry: 'ExtensionRegistry'):
        self.registry = registry

    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call a hook across all extensions."""
        return self.registry.call_hook(hook_name, *args, **kwargs)

    # Common hooks
    def on_template_created(self, template_data: Dict[str, Any]) -> None:
        """Called when a template is created."""
        self.call_hook("on_template_created", template_data)

    def on_workflow_executed(self, workflow_id: str, result: Any) -> None:
        """Called when a workflow is executed."""
        self.call_hook("on_workflow_executed", workflow_id, result)

    def on_asset_added(self, asset_data: Dict[str, Any]) -> None:
        """Called when an asset is added."""
        self.call_hook("on_asset_added", asset_data)

    def on_brand_kit_modified(self, brand_data: Dict[str, Any]) -> None:
        """Called when brand kit is modified."""
        self.call_hook("on_brand_kit_modified", brand_data)

    def on_ui_ready(self) -> None:
        """Called when UI is ready."""
        self.call_hook("on_ui_ready")

    def on_shutdown(self) -> None:
        """Called during shutdown."""
        self.call_hook("on_shutdown")