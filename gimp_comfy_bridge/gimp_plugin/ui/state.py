"""
UI State Management for Comfy Gimpy Studio GIMP Plugin.

Manages toolbox states, panel positions, and UI persistence.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class ToolboxState(Enum):
    """States a toolbox can be in."""
    CLOSED = "closed"
    MINIMIZED = "minimized"
    OPEN = "open"
    FLOATING = "floating"


class ToolboxType(Enum):
    """Types of toolboxes available."""
    TEMPLATES = "templates"
    STYLES = "styles"
    MODELS = "models"
    WORKFLOWS = "workflows"
    FUSION = "fusion"
    TASKS = "tasks"
    MARKETPLACE = "marketplace"
    SETTINGS = "settings"
    BRAND_KITS = "brand_kits"
    LAYOUT_OPTIMIZATION = "layout_optimization"
    EXTENSIONS = "extensions"


@dataclass
class ToolboxConfig:
    """Configuration for a toolbox."""
    toolbox_type: ToolboxType
    state: ToolboxState
    position: Optional[Tuple[int, int]] = None  # (x, y) for floating panels
    size: Optional[Tuple[int, int]] = None  # (width, height) for floating panels
    docked: bool = True
    order: int = 0  # Order in toolbox bar
    expanded_sections: List[str] = None  # Which sections are expanded

    def __post_init__(self):
        if self.expanded_sections is None:
            self.expanded_sections = []


@dataclass
class UIConfig:
    """Overall UI configuration."""
    toolbox_bar_visible: bool = True
    toolbox_bar_position: str = "left"  # "left", "right", "top", "bottom"
    dark_mode: bool = True
    compact_mode: bool = False
    auto_hide_toolbox_bar: bool = False
    toolbox_configs: Dict[str, ToolboxConfig] = None

    def __post_init__(self):
        if self.toolbox_configs is None:
            self.toolbox_configs = self._get_default_toolbox_configs()

    def _get_default_toolbox_configs(self) -> Dict[str, ToolboxConfig]:
        """Get default toolbox configurations."""
        return {
            ToolboxType.TEMPLATES.value: ToolboxConfig(
                toolbox_type=ToolboxType.TEMPLATES,
                state=ToolboxState.CLOSED,
                order=0,
                expanded_sections=["recent", "favorites"]
            ),
            ToolboxType.STYLES.value: ToolboxConfig(
                toolbox_type=ToolboxType.STYLES,
                state=ToolboxState.CLOSED,
                order=1,
                expanded_sections=["recent", "categories"]
            ),
            ToolboxType.MODELS.value: ToolboxConfig(
                toolbox_type=ToolboxType.MODELS,
                state=ToolboxState.CLOSED,
                order=2,
                expanded_sections=["checkpoints", "loras"]
            ),
            ToolboxType.WORKFLOWS.value: ToolboxConfig(
                toolbox_type=ToolboxType.WORKFLOWS,
                state=ToolboxState.CLOSED,
                order=3,
                expanded_sections=["recent", "favorites"]
            ),
            ToolboxType.FUSION.value: ToolboxConfig(
                toolbox_type=ToolboxType.FUSION,
                state=ToolboxState.CLOSED,
                order=4,
                expanded_sections=["layers", "blend_modes"]
            ),
            ToolboxType.TASKS.value: ToolboxConfig(
                toolbox_type=ToolboxType.TASKS,
                state=ToolboxState.MINIMIZED,
                order=5,
                expanded_sections=["queue", "history"]
            ),
            ToolboxType.MARKETPLACE.value: ToolboxConfig(
                toolbox_type=ToolboxType.MARKETPLACE,
                state=ToolboxState.CLOSED,
                order=6,
                expanded_sections=["installed", "browse"]
            ),
            ToolboxType.SETTINGS.value: ToolboxConfig(
                toolbox_type=ToolboxType.SETTINGS,
                state=ToolboxState.CLOSED,
                order=7,
                expanded_sections=["general", "advanced"]
            )
        }


class UIStateManager:
    """Manages UI state persistence and retrieval."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the UI state manager.

        Args:
            config_dir: Directory to store UI configuration. If None, uses default.
        """
        if config_dir is None:
            # Default to GIMP config directory
            try:
                import gimp
                config_dir = Path(gimp.directory) / "plug-ins" / "comfy-gimpy-studio"
            except ImportError:
                # Fallback for development
                config_dir = Path.home() / ".config" / "comfy-gimpy-studio"

        self.config_dir = config_dir
        self.config_file = self.config_dir / "ui_config.json"
        self._config: Optional[UIConfig] = None

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> UIConfig:
        """Get the current UI configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> UIConfig:
        """Load UI configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                return self._deserialize_config(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load UI config: {e}. Using defaults.")
                return UIConfig()
        else:
            return UIConfig()

    def _deserialize_config(self, data: Dict[str, Any]) -> UIConfig:
        """Deserialize UI configuration from dictionary."""
        # Convert toolbox configs
        toolbox_configs = {}
        if "toolbox_configs" in data:
            for key, config_data in data["toolbox_configs"].items():
                # Convert string keys back to ToolboxType enum
                toolbox_type = ToolboxType(config_data["toolbox_type"])
                state = ToolboxState(config_data["state"])
                expanded_sections = config_data.get("expanded_sections", [])

                toolbox_configs[key] = ToolboxConfig(
                    toolbox_type=toolbox_type,
                    state=state,
                    position=tuple(config_data.get("position", [None, None])) if config_data.get("position") else None,
                    size=tuple(config_data.get("size", [None, None])) if config_data.get("size") else None,
                    docked=config_data.get("docked", True),
                    order=config_data.get("order", 0),
                    expanded_sections=expanded_sections
                )

        return UIConfig(
            toolbox_bar_visible=data.get("toolbox_bar_visible", True),
            toolbox_bar_position=data.get("toolbox_bar_position", "left"),
            dark_mode=data.get("dark_mode", True),
            compact_mode=data.get("compact_mode", False),
            auto_hide_toolbox_bar=data.get("auto_hide_toolbox_bar", False),
            toolbox_configs=toolbox_configs
        )

    def save_config(self):
        """Save current UI configuration to file."""
        if self._config is None:
            return

        try:
            data = self._serialize_config(self._config)
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("UI configuration saved")
        except Exception as e:
            logger.error(f"Failed to save UI config: {e}")

    def _serialize_config(self, config: UIConfig) -> Dict[str, Any]:
        """Serialize UI configuration to dictionary."""
        data = {
            "toolbox_bar_visible": config.toolbox_bar_visible,
            "toolbox_bar_position": config.toolbox_bar_position,
            "dark_mode": config.dark_mode,
            "compact_mode": config.compact_mode,
            "auto_hide_toolbox_bar": config.auto_hide_toolbox_bar,
            "toolbox_configs": {}
        }

        for key, toolbox_config in config.toolbox_configs.items():
            data["toolbox_configs"][key] = {
                "toolbox_type": toolbox_config.toolbox_type.value,
                "state": toolbox_config.state.value,
                "position": list(toolbox_config.position) if toolbox_config.position else None,
                "size": list(toolbox_config.size) if toolbox_config.size else None,
                "docked": toolbox_config.docked,
                "order": toolbox_config.order,
                "expanded_sections": toolbox_config.expanded_sections
            }

        return data

    def get_toolbox_config(self, toolbox_type: ToolboxType) -> ToolboxConfig:
        """Get configuration for a specific toolbox."""
        return self.config.toolbox_configs.get(toolbox_type.value, ToolboxConfig(toolbox_type, ToolboxState.CLOSED))

    def set_toolbox_config(self, toolbox_type: ToolboxType, config: ToolboxConfig):
        """Set configuration for a specific toolbox."""
        self.config.toolbox_configs[toolbox_type.value] = config
        self.save_config()

    def update_toolbox_state(self, toolbox_type: ToolboxType, state: ToolboxState):
        """Update the state of a toolbox."""
        config = self.get_toolbox_config(toolbox_type)
        config.state = state
        self.set_toolbox_config(toolbox_type, config)

    def update_toolbox_position(self, toolbox_type: ToolboxType, position: Tuple[int, int]):
        """Update the position of a floating toolbox."""
        config = self.get_toolbox_config(toolbox_type)
        config.position = position
        self.set_toolbox_config(toolbox_type, config)

    def update_toolbox_size(self, toolbox_type: ToolboxType, size: Tuple[int, int]):
        """Update the size of a floating toolbox."""
        config = self.get_toolbox_config(toolbox_type)
        config.size = size
        self.set_toolbox_config(toolbox_type, config)

    def toggle_section_expanded(self, toolbox_type: ToolboxType, section: str):
        """Toggle whether a section is expanded in a toolbox."""
        config = self.get_toolbox_config(toolbox_type)
        if section in config.expanded_sections:
            config.expanded_sections.remove(section)
        else:
            config.expanded_sections.append(section)
        self.set_toolbox_config(toolbox_type, config)

    def reorder_toolboxes(self, toolbox_order: List[ToolboxType]):
        """Update the order of toolboxes in the bar."""
        for i, toolbox_type in enumerate(toolbox_order):
            config = self.get_toolbox_config(toolbox_type)
            config.order = i
            self.set_toolbox_config(toolbox_type, config)

    def get_ordered_toolboxes(self) -> List[Tuple[ToolboxType, ToolboxConfig]]:
        """Get toolboxes ordered by their position in the bar."""
        toolboxes = [(t, c) for t, c in self.config.toolbox_configs.items()]
        toolboxes.sort(key=lambda x: x[1].order)
        return toolboxes

    def reset_to_defaults(self):
        """Reset UI configuration to defaults."""
        self._config = UIConfig()
        self.save_config()
        logger.info("UI configuration reset to defaults")