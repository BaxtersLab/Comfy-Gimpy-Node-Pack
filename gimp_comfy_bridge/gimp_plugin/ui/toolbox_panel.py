"""
Toolbox Panel for Comfy Gimpy Studio GIMP Plugin.

Provides expandable drop-down panels with sections, thumbnails, and controls.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

from .state import UIStateManager, ToolboxType, ToolboxState
from .icons import IconRegistry, IconSize, ToolboxIcon
from .layout import LayoutManager

logger = logging.getLogger(__name__)


class PanelSection:
    """A collapsible section within a toolbox panel."""

    def __init__(self,
                 name: str,
                 title: str,
                 icon: Optional[ToolboxIcon] = None,
                 expanded: bool = True):
        """
        Initialize a panel section.

        Args:
            name: Internal name of the section
            title: Display title
            icon: Optional icon for the section
            expanded: Whether the section starts expanded
        """
        self.name = name
        self.title = title
        self.icon = icon
        self.expanded = expanded
        self._container = None
        self._header = None
        self._content = None
        self._gimp_available = self._check_gimp_availability()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            return True
        except ImportError:
            return False

    def create_ui(self, layout_manager: LayoutManager, icon_registry: IconRegistry) -> Any:
        """
        Create the UI for this section.

        Args:
            layout_manager: Layout manager
            icon_registry: Icon registry

        Returns:
            Container widget
        """
        if not self._gimp_available:
            self._container = f"mock_section_{self.name}"
            return self._container

        try:
            import gimp
            from gimpfu import *

            # Create main container
            self._container = gimp.ui.VBox(spacing=layout_manager.get_spacing("small"))

            # Create header
            self._header = self._create_header(layout_manager, icon_registry)
            self._container.pack_start(self._header, expand=False, fill=False)

            # Create content area
            self._content = gimp.ui.VBox(spacing=layout_manager.get_spacing("tiny"))
            self._container.pack_start(self._content, expand=True, fill=True)

            # Set initial visibility
            self._content.set_visible(self.expanded)

            return self._container

        except Exception as e:
            logger.error(f"Failed to create section UI: {e}")
            self._container = f"mock_section_{self.name}"
            return self._container

    def _create_header(self, layout_manager: LayoutManager, icon_registry: IconRegistry) -> Any:
        """
        Create the section header.

        Args:
            layout_manager: Layout manager
            icon_registry: Icon registry

        Returns:
            Header widget
        """
        if not self._gimp_available:
            return f"mock_header_{self.name}"

        try:
            import gimp
            from gimpfu import *

            # Create header container
            header = gimp.ui.HBox(spacing=layout_manager.get_spacing("small"))

            # Add expand/collapse button
            expand_icon = icon_registry.get_icon(
                ToolboxIcon.EXPAND if not self.expanded else ToolboxIcon.COLLAPSE,
                IconSize.SMALL
            )
            expand_button = gimp.ui.Button()
            # expand_button.set_image(expand_icon)
            expand_button.connect("clicked", self._toggle_expanded)
            header.pack_start(expand_button, expand=False, fill=False)

            # Add icon if provided
            if self.icon:
                icon_widget = icon_registry.get_icon(self.icon, IconSize.SMALL)
                # Would add icon widget here
                pass

            # Add title label
            title_label = gimp.ui.Label(self.title)
            header.pack_start(title_label, expand=True, fill=True)

            # Apply styling
            layout_manager.apply_theme_to_widget(header, "section_header")

            return header

        except Exception as e:
            logger.error(f"Failed to create section header: {e}")
            return f"mock_header_{self.name}"

    def _toggle_expanded(self, button: Any = None):
        """Toggle the expanded state of the section."""
        self.expanded = not self.expanded

        if self._gimp_available and self._content:
            self._content.set_visible(self.expanded)

            # Update expand button icon
            # Would update the icon here

        logger.debug(f"Section {self.name} expanded: {self.expanded}")

    def add_content(self, widget: Any):
        """
        Add content to the section.

        Args:
            widget: Widget to add
        """
        if self._gimp_available and self._content:
            self._content.pack_start(widget, expand=False, fill=False)

    def clear_content(self):
        """Clear all content from the section."""
        if self._gimp_available and self._content:
            for child in self._content.get_children():
                self._content.remove(child)

    def set_expanded(self, expanded: bool):
        """
        Set the expanded state.

        Args:
            expanded: Whether to expand the section
        """
        if self.expanded != expanded:
            self._toggle_expanded()


class ToolboxPanel:
    """Drop-down expandable toolbox panel."""

    def __init__(self,
                 toolbox_type: ToolboxType,
                 state_manager: UIStateManager,
                 icon_registry: IconRegistry,
                 layout_manager: LayoutManager):
        """
        Initialize the toolbox panel.

        Args:
            toolbox_type: Type of toolbox
            state_manager: UI state manager
            icon_registry: Icon registry
            layout_manager: Layout manager
        """
        self.toolbox_type = toolbox_type
        self.state_manager = state_manager
        self.icon_registry = icon_registry
        self.layout_manager = layout_manager

        self._gimp_available = self._check_gimp_availability()
        self._container = None
        self._sections: Dict[str, PanelSection] = {}
        self._current_height = 0
        self._max_height = layout_manager.config.toolbox_panel_max_height

        # Callbacks
        self.on_section_toggle: Optional[Callable[[str, bool], None]] = None
        self.on_panel_close: Optional[Callable[[], None]] = None

        # Create UI
        self._create_ui()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP UI libraries are available."""
        try:
            import gimp
            return True
        except ImportError:
            return False

    def _create_ui(self):
        """Create the toolbox panel UI."""
        if not self._gimp_available:
            self._container = f"mock_panel_{self.toolbox_type.value}"
            self._create_mock_sections()
            return

        try:
            import gimp
            from gimpfu import *

            # Create main container
            self._container = gimp.ui.Frame()
            self._container.set_shadow_type(gimp.SHADOW_OUT)

            # Create scrollable content area
            scrolled = gimp.ui.ScrolledWindow()
            scrolled.set_policy(gimp.POLICY_NEVER, gimp.POLICY_AUTOMATIC)

            content_box = gimp.ui.VBox(spacing=self.layout_manager.get_spacing("small"))
            scrolled.add_with_viewport(content_box)

            self._container.add(scrolled)

            # Set size
            width, height = self.layout_manager.calculate_panel_size(280, 400)
            self._container.set_size_request(width, height)

            # Apply styling
            self.layout_manager.apply_theme_to_widget(self._container, "toolbox_panel")

            # Create sections based on toolbox type
            self._create_sections(content_box)

            logger.debug(f"Toolbox panel created for {self.toolbox_type}")

        except Exception as e:
            logger.error(f"Failed to create toolbox panel UI: {e}")
            self._container = f"mock_panel_{self.toolbox_type.value}"
            self._create_mock_sections()

    def _create_mock_sections(self):
        """Create mock sections for development."""
        section_names = self._get_section_names_for_toolbox()
        for name in section_names:
            section = PanelSection(name, name.title(), expanded=True)
            self._sections[name] = section

    def _get_section_names_for_toolbox(self) -> List[str]:
        """Get section names for this toolbox type."""
        sections_map = {
            ToolboxType.TEMPLATES: ["recent", "favorites", "categories", "generate", "search"],
            ToolboxType.STYLES: ["recent", "categories", "presets", "custom"],
            ToolboxType.MODELS: ["checkpoints", "loras", "embeddings", "upscalers"],
            ToolboxType.WORKFLOWS: ["recent", "favorites", "categories", "builder"],
            ToolboxType.FUSION: ["layers", "blend_modes", "masks", "effects"],
            ToolboxType.TASKS: ["queue", "running", "completed", "failed"],
            ToolboxType.MARKETPLACE: ["installed", "browse", "categories", "search"],
            ToolboxType.SETTINGS: ["general", "appearance", "performance", "advanced"],
            ToolboxType.BRAND_KITS: ["recent", "favorites", "categories", "create", "apply"],
            ToolboxType.LAYOUT_OPTIMIZATION: ["analyze", "optimize", "variants", "overlays", "settings"]
        }
        return sections_map.get(self.toolbox_type, ["general"])

    def _create_sections(self, container: Any):
        """Create sections for this toolbox."""
        section_names = self._get_section_names_for_toolbox()

        for name in section_names:
            section = PanelSection(
                name=name,
                title=name.title(),
                expanded=self._is_section_expanded(name)
            )

            section_ui = section.create_ui(self.layout_manager, self.icon_registry)
            if section_ui:
                container.pack_start(section_ui, expand=False, fill=False)
                self._sections[name] = section

                # Populate section content
                self._populate_section_content(section)

    def _is_section_expanded(self, section_name: str) -> bool:
        """Check if a section should be expanded."""
        config = self.state_manager.get_toolbox_config(self.toolbox_type)
        return section_name in config.expanded_sections

    def _populate_section_content(self, section: PanelSection):
        """Populate content for a section."""
        if self.toolbox_type == ToolboxType.TEMPLATES:
            self._populate_templates_section(section)
        elif self.toolbox_type == ToolboxType.STYLES:
            self._populate_styles_section(section)
        elif self.toolbox_type == ToolboxType.TASKS:
            self._populate_tasks_section(section)
        elif self.toolbox_type == ToolboxType.SETTINGS:
            self._populate_settings_section(section)
        elif self.toolbox_type == ToolboxType.BRAND_KITS:
            self._populate_brand_kits_section(section)
        elif self.toolbox_type == ToolboxType.LAYOUT_OPTIMIZATION:
            self._populate_layout_optimization_section(section)
        elif self.toolbox_type == ToolboxType.EXTENSIONS:
            self._populate_extensions_section(section)
        else:
            # Generic content for other toolboxes
            self._populate_generic_section(section)

    def _populate_templates_section(self, section: PanelSection):
        """Populate content for templates section."""
        if section.name == "recent":
            # Add recent templates list
            self._add_item_list(section, ["Template 1", "Template 2", "Template 3"])
        elif section.name == "favorites":
            self._add_item_list(section, ["Favorite A", "Favorite B"])
        elif section.name == "generate":
            self._populate_generate_section(section)
        elif section.name == "search":
            self._add_search_box(section)

    def _populate_styles_section(self, section: PanelSection):
        """Populate content for styles section."""
        if section.name == "presets":
            self._add_item_grid(section, ["Style 1", "Style 2", "Style 3", "Style 4"])
        elif section.name == "custom":
            self._add_button(section, "Create New Style", self._on_create_style)

    def _populate_tasks_section(self, section: PanelSection):
        """Populate content for tasks section."""
        if section.name == "queue":
            self._add_task_list(section, "queued")
        elif section.name == "running":
            self._add_task_list(section, "running")
        elif section.name == "completed":
            self._add_task_list(section, "completed")

    def _populate_settings_section(self, section: PanelSection):
        """Populate content for settings section."""
        if section.name == "appearance":
            self._add_toggle(section, "Dark Mode", True, self._on_dark_mode_toggle)
            self._add_toggle(section, "Compact Mode", False, self._on_compact_mode_toggle)
        elif section.name == "performance":
            self._add_slider(section, "Max Workers", 1, 8, 4, self._on_max_workers_change)

    def _populate_generate_section(self, section: PanelSection):
        """Populate content for template generation section."""
        # Add generation method buttons
        self._add_button(section, "Generate from Prompt", self._on_generate_from_prompt)
        self._add_button(section, "Generate from Image", self._on_generate_from_image)
        self._add_button(section, "Generate from Workflow", self._on_generate_from_workflow)
        self._add_button(section, "Enhance Template", self._on_enhance_template)

        # Add category selector
        self._add_category_selector(section)

        # Add options toggles
        self._add_toggle(section, "Generate Variants", True, self._on_variants_toggle)
        self._add_toggle(section, "Include Previews", True, self._on_previews_toggle)

        # Add variant count slider
        self._add_slider(section, "Variant Count", 1, 10, 3, self._on_variant_count_change)

    def _populate_brand_kits_section(self, section: PanelSection):
        """Populate content for brand kits section."""
        if section.name == "recent":
            # Show recently used brand kits
            self._add_label(section, "Recent Brand Kits")
            recent_kits = ["brand_kit_1", "brand_kit_2", "brand_kit_3"]  # Mock data
            self._add_item_list(section, recent_kits)

        elif section.name == "favorites":
            # Show favorite brand kits
            self._add_label(section, "Favorite Brand Kits")
            favorite_kits = ["favorite_brand_1", "favorite_brand_2"]  # Mock data
            self._add_item_list(section, favorite_kits)

        elif section.name == "categories":
            # Show brand kit categories
            self._add_label(section, "Brand Kit Categories")
            categories = ["Corporate", "Personal", "Seasonal", "Product", "Event"]
            self._add_item_grid(section, categories, 2)

        elif section.name == "create":
            # Brand kit creation tools
            self._add_button(section, "Create New Brand Kit", self._on_create_brand_kit)
            self._add_button(section, "Import Brand Kit", self._on_import_brand_kit)
            self._add_button(section, "Extract from Image", self._on_extract_brand_kit)

        elif section.name == "apply":
            # Brand kit application tools
            self._add_button(section, "Apply to Template", self._on_apply_brand_kit_template)
            self._add_button(section, "Apply to Style", self._on_apply_brand_kit_style)
            self._add_button(section, "Apply to Workflow", self._on_apply_brand_kit_workflow)
            self._add_button(section, "Preview Application", self._on_preview_brand_kit)

    def _populate_layout_optimization_section(self, section: PanelSection):
        """Populate content for layout optimization section."""
        if section.name == "analyze":
            self._add_button(section, "Analyze Current Layout", self._on_analyze_layout)
            self._add_toggle(section, "Auto-analyze on changes", False, self._on_toggle_auto_analyze)
        elif section.name == "optimize":
            self._add_button(section, "Optimize Layout", self._on_optimize_layout)
            self._add_combo_box(section, "Optimization Level", ["basic", "standard", "advanced"],
                              "standard", self._on_optimization_level_changed)
        elif section.name == "variants":
            self._add_button(section, "Generate Variants", self._on_generate_variants)
            self._add_slider(section, "Variants Count", 1, 10, 3, self._on_variants_count_changed)
        elif section.name == "overlays":
            self._add_toggle(section, "Show Alignment Guides", True, self._on_toggle_alignment_guides)
            self._add_toggle(section, "Show Spacing Indicators", True, self._on_toggle_spacing_indicators)
            self._add_toggle(section, "Show Rule of Thirds", False, self._on_toggle_rule_of_thirds)
        elif section.name == "settings":
            self._add_toggle(section, "Brand-aware Optimization", True, self._on_toggle_brand_aware)
            self._add_button(section, "Reset to Defaults", self._on_reset_layout_settings)

    def _populate_generic_section(self, section: PanelSection):
        """Populate generic content for sections."""
        self._add_label(section, f"Content for {section.name}")

    def _add_item_list(self, section: PanelSection, items: List[str]):
        """Add a list of items to a section."""
        for item in items:
            button = self._create_button(item, lambda b, i=item: self._on_item_click(i))
            section.add_content(button)

    def _add_item_grid(self, section: PanelSection, items: List[str], columns: int = 2):
        """Add a grid of items to a section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            grid = gimp.ui.Table(rows=len(items)//columns + 1, columns=columns)
            grid.set_homogeneous(True)

            for i, item in enumerate(items):
                row, col = divmod(i, columns)
                button = self._create_button(item, lambda b, i=item: self._on_item_click(i))
                grid.attach(button, col, col+1, row, row+1)

            section.add_content(grid)
        except Exception as e:
            logger.error(f"Failed to create item grid: {e}")

    def _add_search_box(self, section: PanelSection):
        """Add a search box to a section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            search_box = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))

            entry = gimp.ui.Entry()
            entry.set_text("Search...")
            search_box.pack_start(entry, expand=True, fill=True)

            search_button = self._create_button("Search", self._on_search)
            search_box.pack_start(search_button, expand=False, fill=False)

            section.add_content(search_box)
        except Exception as e:
            logger.error(f"Failed to create search box: {e}")

    def _add_button(self, section: PanelSection, label: str, callback: Callable):
        """Add a button to a section."""
        button = self._create_button(label, callback)
        section.add_content(button)

    def _add_toggle(self, section: PanelSection, label: str, initial: bool, callback: Callable):
        """Add a toggle control to a section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            hbox = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))

            toggle = gimp.ui.CheckButton(label)
            toggle.set_active(initial)
            toggle.connect("toggled", callback)
            hbox.pack_start(toggle, expand=True, fill=True)

            section.add_content(hbox)
        except Exception as e:
            logger.error(f"Failed to create toggle: {e}")

    def _add_slider(self, section: PanelSection, label: str, min_val: int, max_val: int,
                   initial: int, callback: Callable):
        """Add a slider control to a section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            vbox = gimp.ui.VBox(spacing=self.layout_manager.get_spacing("tiny"))

            label_widget = gimp.ui.Label(label)
            vbox.pack_start(label_widget, expand=False, fill=False)

            hbox = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))

            slider = gimp.ui.HScale()
            slider.set_range(min_val, max_val)
            slider.set_value(initial)
            slider.connect("value-changed", callback)
            hbox.pack_start(slider, expand=True, fill=True)

            value_label = gimp.ui.Label(str(initial))
            hbox.pack_start(value_label, expand=False, fill=False)

            vbox.pack_start(hbox, expand=False, fill=False)
            section.add_content(vbox)
        except Exception as e:
            logger.error(f"Failed to create slider: {e}")

    def _add_label(self, section: PanelSection, text: str):
        """Add a label to a section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            label = gimp.ui.Label(text)
            section.add_content(label)
        except Exception as e:
            logger.error(f"Failed to create label: {e}")

    def _add_task_list(self, section: PanelSection, status: str):
        """Add a task list for a specific status."""
        # Mock task data - in real implementation, this would come from task engine
        mock_tasks = {
            "queued": ["Task 1", "Task 2"],
            "running": ["Task 3"],
            "completed": ["Task 4", "Task 5"]
        }

        tasks = mock_tasks.get(status, [])
        for task in tasks:
            hbox = self._create_task_item(task, status)
            section.add_content(hbox)

    def _create_task_item(self, task_name: str, status: str) -> Any:
        """Create a task item widget."""
        if not self._gimp_available:
            return f"mock_task_{task_name}"

        try:
            import gimp
            from gimpfu import *

            hbox = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))

            # Status icon
            status_icon = self.icon_registry.get_status_icon(status)
            # Would add status icon here

            # Task name
            label = gimp.ui.Label(task_name)
            hbox.pack_start(label, expand=True, fill=True)

            # Action button (cancel for running, etc.)
            if status == "running":
                cancel_button = self._create_button("Cancel", lambda b: self._on_cancel_task(task_name))
                hbox.pack_start(cancel_button, expand=False, fill=False)

            return hbox
        except Exception as e:
            logger.error(f"Failed to create task item: {e}")
            return f"mock_task_{task_name}"

    def _create_button(self, label: str, callback: Callable) -> Any:
        """Create a button with consistent styling."""
        if not self._gimp_available:
            return f"mock_button_{label}"

        try:
            import gimp
            from gimpfu import *

            button = gimp.ui.Button(label)
            button.connect("clicked", callback)
            self.layout_manager.apply_theme_to_widget(button, "panel_button")
            return button
        except Exception as e:
            logger.error(f"Failed to create button: {e}")
            return f"mock_button_{label}"

    def _on_item_click(self, item: str):
        """Handle item click."""
        logger.debug(f"Item clicked: {item}")

    def _on_search(self, button: Any):
        """Handle search."""
        logger.debug("Search triggered")

    def _on_create_style(self, button: Any):
        """Handle create style."""
        logger.debug("Create style triggered")

    def _on_dark_mode_toggle(self, toggle: Any):
        """Handle dark mode toggle."""
        active = toggle.get_active()
        self.layout_manager.update_theme(active, self.layout_manager.config.compact_mode)
        logger.debug(f"Dark mode toggled: {active}")

    def _on_compact_mode_toggle(self, toggle: Any):
        """Handle compact mode toggle."""
        active = toggle.get_active()
        self.layout_manager.update_theme(self.layout_manager.config.dark_mode, active)
        logger.debug(f"Compact mode toggled: {active}")

    def _on_max_workers_change(self, slider: Any):
        """Handle max workers change."""
        value = int(slider.get_value())
        logger.debug(f"Max workers changed: {value}")

    def _on_generate_from_prompt(self, button: Any):
        """Handle generate from prompt."""
        logger.debug("Generate from prompt triggered")
        # TODO: Open prompt dialog and trigger generation

    def _on_generate_from_image(self, button: Any):
        """Handle generate from image."""
        logger.debug("Generate from image triggered")
        # TODO: Open image selector and trigger generation

    def _on_generate_from_workflow(self, button: Any):
        """Handle generate from workflow."""
        logger.debug("Generate from workflow triggered")
        # TODO: Open workflow selector and trigger generation

    def _on_enhance_template(self, button: Any):
        """Handle enhance template."""
        logger.debug("Enhance template triggered")
        # TODO: Open template selector and enhancement dialog

    def _add_category_selector(self, section: PanelSection):
        """Add category selector to section."""
        if not self._gimp_available:
            return

        try:
            import gimp
            from gimpfu import *

            # Create combo box for categories
            categories = ["general", "poster", "brochure", "website", "business_card",
                         "flyer", "banner", "social_media", "presentation", "newsletter",
                         "menu", "certificate", "invitation", "logo", "packaging",
                         "infographic", "resume", "letterhead", "envelope"]

            combo = gimp.ui.ComboBox()
            for category in categories:
                combo.append_text(category.title())

            combo.set_active(0)  # Default to general
            combo.connect("changed", self._on_category_changed)

            # Add label
            hbox = gimp.ui.HBox(spacing=self.layout_manager.get_spacing("small"))
            label = gimp.ui.Label("Category:")
            hbox.pack_start(label, expand=False, fill=False)
            hbox.pack_start(combo, expand=True, fill=True)

            section.add_content(hbox)
        except Exception as e:
            logger.error(f"Failed to create category selector: {e}")

    def _on_category_changed(self, combo: Any):
        """Handle category selection change."""
        active = combo.get_active()
        if active >= 0:
            categories = ["general", "poster", "brochure", "website", "business_card",
                         "flyer", "banner", "social_media", "presentation", "newsletter",
                         "menu", "certificate", "invitation", "logo", "packaging",
                         "infographic", "resume", "letterhead", "envelope"]
            selected = categories[active]
            logger.debug(f"Category changed: {selected}")

    def _on_variants_toggle(self, toggle: Any):
        """Handle variants toggle."""
        active = toggle.get_active()
        logger.debug(f"Generate variants toggled: {active}")

    def _on_previews_toggle(self, toggle: Any):
        """Handle previews toggle."""
        active = toggle.get_active()
        logger.debug(f"Include previews toggled: {active}")

    def _on_variant_count_change(self, slider: Any):
        """Handle variant count change."""
        value = int(slider.get_value())
        logger.debug(f"Variant count changed: {value}")

    def _on_cancel_task(self, task_name: str):
        """Handle task cancellation."""
        logger.debug(f"Cancel task: {task_name}")

    # Brand Kit Callbacks
    def _on_create_brand_kit(self, button: Any):
        """Handle create brand kit button."""
        logger.debug("Create brand kit clicked")
        # TODO: Open brand kit creation dialog

    def _on_import_brand_kit(self, button: Any):
        """Handle import brand kit button."""
        logger.debug("Import brand kit clicked")
        # TODO: Open file dialog for brand kit import

    def _on_extract_brand_kit(self, button: Any):
        """Handle extract brand kit from image button."""
        logger.debug("Extract brand kit from image clicked")
        # TODO: Extract colors/fonts from current image

    def _on_apply_brand_kit_template(self, button: Any):
        """Handle apply brand kit to template button."""
        logger.debug("Apply brand kit to template clicked")
        # TODO: Apply selected brand kit to current template

    def _on_apply_brand_kit_style(self, button: Any):
        """Handle apply brand kit to style button."""
        logger.debug("Apply brand kit to style clicked")
        # TODO: Apply selected brand kit to current style

    def _on_apply_brand_kit_workflow(self, button: Any):
        """Handle apply brand kit to workflow button."""
        logger.debug("Apply brand kit to workflow clicked")
        # TODO: Apply selected brand kit to current workflow

    def _on_preview_brand_kit(self, button: Any):
        """Handle preview brand kit application button."""
        logger.debug("Preview brand kit application clicked")
        # TODO: Show preview of brand kit application

    # Layout Optimization Callbacks
    def _on_analyze_layout(self, button: Any):
        """Handle analyze layout button."""
        logger.debug("Analyze layout clicked")
        # TODO: Analyze current layout and show results

    def _on_toggle_auto_analyze(self, toggle: Any):
        """Handle auto-analyze toggle."""
        active = toggle.get_active()
        logger.debug(f"Auto-analyze toggled: {active}")
        # TODO: Enable/disable automatic layout analysis

    def _on_optimize_layout(self, button: Any):
        """Handle optimize layout button."""
        logger.debug("Optimize layout clicked")
        # TODO: Run layout optimization

    def _on_optimization_level_changed(self, combo: Any):
        """Handle optimization level change."""
        level = combo.get_active_text()
        logger.debug(f"Optimization level changed to: {level}")
        # TODO: Update optimization level setting

    def _on_generate_variants(self, button: Any):
        """Handle generate variants button."""
        logger.debug("Generate variants clicked")
        # TODO: Generate layout variants

    def _on_variants_count_changed(self, slider: Any):
        """Handle variants count change."""
        count = slider.get_value()
        logger.debug(f"Variants count changed to: {count}")
        # TODO: Update variants count setting

    def _on_toggle_alignment_guides(self, toggle: Any):
        """Handle alignment guides toggle."""
        active = toggle.get_active()
        logger.debug(f"Alignment guides toggled: {active}")
        # TODO: Show/hide alignment guides overlay

    def _on_toggle_spacing_indicators(self, toggle: Any):
        """Handle spacing indicators toggle."""
        active = toggle.get_active()
        logger.debug(f"Spacing indicators toggled: {active}")
        # TODO: Show/hide spacing indicators overlay

    def _on_toggle_rule_of_thirds(self, toggle: Any):
        """Handle rule of thirds toggle."""
        active = toggle.get_active()
        logger.debug(f"Rule of thirds toggled: {active}")
        # TODO: Show/hide rule of thirds overlay

    def _on_toggle_brand_aware(self, toggle: Any):
        """Handle brand-aware optimization toggle."""
        active = toggle.get_active()
        logger.debug(f"Brand-aware optimization toggled: {active}")
        # TODO: Enable/disable brand-aware optimization

    def _on_reset_layout_settings(self, button: Any):
        """Handle reset layout settings button."""
        logger.debug("Reset layout settings clicked")
        # TODO: Reset all layout optimization settings to defaults

    def _populate_extensions_section(self, section: PanelSection):
        """Populate content for extensions section."""
        if section.name == "installed":
            # Show installed extensions
            self._add_label(section, "Installed Extensions")
            installed_exts = ["extension_1", "extension_2", "extension_3"]  # Mock data
            for ext in installed_exts:
                self._add_toggle(section, ext, True, self._on_extension_toggle)

        elif section.name == "available":
            # Show available extensions to install
            self._add_label(section, "Available Extensions")
            available_exts = ["new_extension_1", "new_extension_2"]  # Mock data
            for ext in available_exts:
                self._add_button(section, f"Install {ext}", self._on_install_extension)

        elif section.name == "settings":
            # Extension settings
            self._add_toggle(section, "Auto-update Extensions", True, self._on_auto_update_toggle)
            self._add_toggle(section, "Hot-reload Enabled", True, self._on_hot_reload_toggle)
            self._add_button(section, "Reload All Extensions", self._on_reload_extensions)

    def _on_extension_toggle(self, toggle: Any):
        """Handle extension enable/disable toggle."""
        active = toggle.get_active()
        extension_name = getattr(toggle, '_extension_name', 'unknown')
        logger.debug(f"Extension {extension_name} toggled: {active}")
        # TODO: Enable/disable extension

    def _on_install_extension(self, button: Any):
        """Handle extension installation."""
        extension_name = getattr(button, '_extension_name', 'unknown')
        logger.debug(f"Installing extension: {extension_name}")
        # TODO: Install extension from marketplace

    def _on_auto_update_toggle(self, toggle: Any):
        """Handle auto-update extensions toggle."""
        active = toggle.get_active()
        logger.debug(f"Auto-update extensions toggled: {active}")
        # TODO: Enable/disable auto-updates

    def _on_hot_reload_toggle(self, toggle: Any):
        """Handle hot-reload toggle."""
        active = toggle.get_active()
        logger.debug(f"Hot-reload toggled: {active}")
        # TODO: Enable/disable hot-reload

    def _on_reload_extensions(self, button: Any):
        """Handle reload all extensions button."""
        logger.debug("Reloading all extensions")
        # TODO: Reload all extensions

    def get_container(self) -> Any:
        """Get the main container widget."""
        return self._container

    def show(self):
        """Show the panel."""
        if self._gimp_available and self._container:
            self._container.show_all()

    def hide(self):
        """Hide the panel."""
        if self._gimp_available and self._container:
            self._container.hide()

    def toggle_section(self, section_name: str):
        """Toggle a section's expanded state."""
        if section_name in self._sections:
            section = self._sections[section_name]
            section.set_expanded(not section.expanded)

            # Update state
            if section.expanded:
                self.state_manager.toggle_section_expanded(self.toolbox_type, section_name)
            else:
                config = self.state_manager.get_toolbox_config(self.toolbox_type)
                if section_name in config.expanded_sections:
                    config.expanded_sections.remove(section_name)
                    self.state_manager.set_toolbox_config(self.toolbox_type, config)

            if self.on_section_toggle:
                self.on_section_toggle(section_name, section.expanded)

    def get_preferred_size(self) -> Tuple[int, int]:
        """Get the preferred size of the panel."""
        width = self.layout_manager.config.toolbox_panel_width
        height = min(self._current_height, self._max_height)
        return width, height

    def update_content(self):
        """Update the panel content (e.g., after data changes)."""
        # Clear and repopulate sections
        for section in self._sections.values():
            section.clear_content()
            self._populate_section_content(section)

        logger.debug(f"Panel content updated for {self.toolbox_type}")