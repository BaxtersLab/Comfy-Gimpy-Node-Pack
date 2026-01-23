"""
Visual Overlays for Layout Optimization.

Generates visual overlays to show suggested layout improvements.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path

from .analyzer import LayoutAnalysis, BoundingBox
from .optimizer import OptimizationAction, OptimizationActionType

logger = logging.getLogger(__name__)


class OverlayType(Enum):
    """Types of visual overlays."""
    ALIGNMENT_GUIDES = "alignment_guides"
    SPACING_INDICATORS = "spacing_indicators"
    CONTRAST_WARNINGS = "contrast_warnings"
    SUGGESTED_MOVES = "suggested_moves"
    SIZE_SUGGESTIONS = "size_suggestions"
    RULE_OF_THIRDS = "rule_of_thirds"
    GOLDEN_RATIO = "golden_ratio"
    VISUAL_HIERARCHY = "visual_hierarchy"


@dataclass
class OverlayElement:
    """Represents a single overlay element."""
    overlay_type: OverlayType
    x: float
    y: float
    width: float
    height: float
    color: str = "#FF6B6B"
    opacity: float = 0.7
    label: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutOverlay:
    """Complete set of visual overlays for a layout."""
    canvas_width: float
    canvas_height: float
    overlays: List[OverlayElement] = field(default_factory=list)
    overlay_types: List[OverlayType] = field(default_factory=list)

    def add_overlay(self, overlay: OverlayElement):
        """Add an overlay element."""
        self.overlays.append(overlay)
        if overlay.overlay_type not in self.overlay_types:
            self.overlay_types.append(overlay.overlay_type)

    def get_overlays_by_type(self, overlay_type: OverlayType) -> List[OverlayElement]:
        """Get overlays of a specific type."""
        return [o for o in self.overlays if o.overlay_type == overlay_type]

    def to_svg(self) -> str:
        """Convert overlays to SVG format for display."""
        svg_elements = []

        for overlay in self.overlays:
            if overlay.overlay_type == OverlayType.ALIGNMENT_GUIDES:
                svg_elements.append(self._overlay_to_svg_line(overlay))
            elif overlay.overlay_type in [OverlayType.SPACING_INDICATORS, OverlayType.SUGGESTED_MOVES]:
                svg_elements.append(self._overlay_to_svg_arrow(overlay))
            elif overlay.overlay_type in [OverlayType.CONTRAST_WARNINGS, OverlayType.SIZE_SUGGESTIONS]:
                svg_elements.append(self._overlay_to_svg_box(overlay))
            else:
                svg_elements.append(self._overlay_to_svg_generic(overlay))

        svg_content = "\n".join(svg_elements)

        return f"""<svg width="{self.canvas_width}" height="{self.canvas_height}" xmlns="http://www.w3.org/2000/svg">
<style>
.overlay-element {{ stroke-width: 2; fill: none; }}
.overlay-label {{ font-family: Arial, sans-serif; font-size: 12px; fill: #333; }}
</style>
{svg_content}
</svg>"""

    def _overlay_to_svg_line(self, overlay: OverlayElement) -> str:
        """Convert alignment guide to SVG line."""
        return f'<line x1="{overlay.x}" y1="{overlay.y}" x2="{overlay.x + overlay.width}" y2="{overlay.y + overlay.height}" stroke="{overlay.color}" stroke-width="1" opacity="{overlay.opacity}" class="overlay-element"/>'

    def _overlay_to_svg_arrow(self, overlay: OverlayElement) -> str:
        """Convert arrow overlay to SVG."""
        # Simple arrow representation
        return f'<polygon points="{overlay.x},{overlay.y} {overlay.x + overlay.width},{overlay.y + overlay.height/2} {overlay.x},{overlay.y + overlay.height}" fill="{overlay.color}" opacity="{overlay.opacity}"/>'

    def _overlay_to_svg_box(self, overlay: OverlayElement) -> str:
        """Convert box overlay to SVG."""
        return f'<rect x="{overlay.x}" y="{overlay.y}" width="{overlay.width}" height="{overlay.height}" stroke="{overlay.color}" fill="none" stroke-dasharray="5,5" opacity="{overlay.opacity}" class="overlay-element"/>'

    def _overlay_to_svg_generic(self, overlay: OverlayElement) -> str:
        """Convert generic overlay to SVG circle."""
        center_x = overlay.x + overlay.width / 2
        center_y = overlay.y + overlay.height / 2
        radius = min(overlay.width, overlay.height) / 4

        return f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{overlay.color}" opacity="{overlay.opacity}"/>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert overlay to dictionary for serialization."""
        return {
            'canvas_width': self.canvas_width,
            'canvas_height': self.canvas_height,
            'overlays': [
                {
                    'type': o.overlay_type.value,
                    'x': o.x,
                    'y': o.y,
                    'width': o.width,
                    'height': o.height,
                    'color': o.color,
                    'opacity': o.opacity,
                    'label': o.label,
                    'description': o.description,
                    'metadata': o.metadata
                }
                for o in self.overlays
            ],
            'overlay_types': [t.value for t in self.overlay_types]
        }


class OverlayGenerator:
    """Generates visual overlays for layout optimization suggestions."""

    def __init__(self):
        self.default_colors = {
            OverlayType.ALIGNMENT_GUIDES: "#4ECDC4",
            OverlayType.SPACING_INDICATORS: "#45B7D1",
            OverlayType.CONTRAST_WARNINGS: "#FFA07A",
            OverlayType.SUGGESTED_MOVES: "#98D8C8",
            OverlayType.SIZE_SUGGESTIONS: "#F7DC6F",
            OverlayType.RULE_OF_THIRDS: "#BB8FCE",
            OverlayType.GOLDEN_RATIO: "#85C1E9",
            OverlayType.VISUAL_HIERARCHY: "#F8C471"
        }

    async def generate_overlays(self, analysis: LayoutAnalysis,
                              actions: Optional[List[OptimizationAction]] = None,
                              overlay_types: Optional[List[OverlayType]] = None) -> LayoutOverlay:
        """
        Generate visual overlays for layout analysis and optimization actions.

        Args:
            analysis: Layout analysis to generate overlays for
            actions: Optional optimization actions to visualize
            overlay_types: Specific overlay types to generate

        Returns:
            LayoutOverlay with visual suggestions
        """
        overlay = LayoutOverlay(
            canvas_width=analysis.canvas_width,
            canvas_height=analysis.canvas_height
        )

        # Default overlay types if not specified
        if overlay_types is None:
            overlay_types = [
                OverlayType.ALIGNMENT_GUIDES,
                OverlayType.SPACING_INDICATORS,
                OverlayType.RULE_OF_THIRDS
            ]

        # Generate overlays for each type
        for overlay_type in overlay_types:
            try:
                if overlay_type == OverlayType.ALIGNMENT_GUIDES:
                    await self._generate_alignment_guides(overlay, analysis)
                elif overlay_type == OverlayType.SPACING_INDICATORS:
                    await self._generate_spacing_indicators(overlay, analysis)
                elif overlay_type == OverlayType.CONTRAST_WARNINGS:
                    await self._generate_contrast_warnings(overlay, analysis)
                elif overlay_type == OverlayType.SUGGESTED_MOVES and actions:
                    await self._generate_suggested_moves(overlay, actions)
                elif overlay_type == OverlayType.SIZE_SUGGESTIONS and actions:
                    await self._generate_size_suggestions(overlay, actions)
                elif overlay_type == OverlayType.RULE_OF_THIRDS:
                    await self._generate_rule_of_thirds(overlay, analysis)
                elif overlay_type == OverlayType.GOLDEN_RATIO:
                    await self._generate_golden_ratio(overlay, analysis)
                elif overlay_type == OverlayType.VISUAL_HIERARCHY:
                    await self._generate_visual_hierarchy(overlay, analysis)
            except Exception as e:
                logger.warning(f"Failed to generate {overlay_type.value} overlay: {e}")

        return overlay

    async def _generate_alignment_guides(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate alignment guide overlays."""
        if len(analysis.elements) < 2:
            return

        # Find common alignment lines
        left_edges = sorted(set(round(e.bounding_box.x, 0) for e in analysis.elements))
        top_edges = sorted(set(round(e.bounding_box.y, 0) for e in analysis.elements))
        right_edges = sorted(set(round(e.bounding_box.x + e.bounding_box.width, 0) for e in analysis.elements))
        bottom_edges = sorted(set(round(e.bounding_box.y + e.bounding_box.height, 0) for e in analysis.elements))

        # Add guides for edges used by multiple elements
        for edges, orientation in [(left_edges, 'vertical'), (top_edges, 'horizontal')]:
            for edge_pos in edges:
                count = sum(1 for e in analysis.elements
                          if abs((e.bounding_box.x if orientation == 'vertical'
                                else e.bounding_box.y) - edge_pos) < 5)
                if count >= 2:  # At least 2 elements aligned
                    if orientation == 'vertical':
                        overlay.add_overlay(OverlayElement(
                            overlay_type=OverlayType.ALIGNMENT_GUIDES,
                            x=edge_pos,
                            y=0,
                            width=0,
                            height=analysis.canvas_height,
                            color=self.default_colors[OverlayType.ALIGNMENT_GUIDES],
                            opacity=0.5,
                            label=f"Align {count} elements",
                            description=f"Vertical alignment guide at x={edge_pos}"
                        ))
                    else:
                        overlay.add_overlay(OverlayElement(
                            overlay_type=OverlayType.ALIGNMENT_GUIDES,
                            x=0,
                            y=edge_pos,
                            width=analysis.canvas_width,
                            height=0,
                            color=self.default_colors[OverlayType.ALIGNMENT_GUIDES],
                            opacity=0.5,
                            label=f"Align {count} elements",
                            description=f"Horizontal alignment guide at y={edge_pos}"
                        ))

    async def _generate_spacing_indicators(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate spacing indicator overlays."""
        elements = sorted(analysis.elements, key=lambda e: e.bounding_box.x)

        for i in range(len(elements) - 1):
            elem1 = elements[i]
            elem2 = elements[i + 1]

            # Check horizontal spacing
            if not elem1.bounding_box.overlaps(elem2.bounding_box):
                spacing = elem2.bounding_box.x - (elem1.bounding_box.x + elem1.bounding_box.width)
                if spacing > 10:  # Only show significant spacing
                    # Add spacing indicator
                    spacing_x = elem1.bounding_box.x + elem1.bounding_box.width
                    spacing_y = min(elem1.bounding_box.y, elem2.bounding_box.y)

                    overlay.add_overlay(OverlayElement(
                        overlay_type=OverlayType.SPACING_INDICATORS,
                        x=spacing_x,
                        y=spacing_y,
                        width=spacing,
                        height=max(elem1.bounding_box.height, elem2.bounding_box.height),
                        color=self.default_colors[OverlayType.SPACING_INDICATORS],
                        opacity=0.3,
                        label=f"{spacing:.0f}px",
                        description=f"Horizontal spacing between {elem1.element_id} and {elem2.element_id}"
                    ))

    async def _generate_contrast_warnings(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate contrast warning overlays."""
        for element in analysis.text_elements:
            # Simple contrast check (would need actual color analysis)
            if element.font_size and element.font_size < 12:
                overlay.add_overlay(OverlayElement(
                    overlay_type=OverlayType.CONTRAST_WARNINGS,
                    x=element.bounding_box.x - 5,
                    y=element.bounding_box.y - 5,
                    width=element.bounding_box.width + 10,
                    height=element.bounding_box.height + 10,
                    color=self.default_colors[OverlayType.CONTRAST_WARNINGS],
                    opacity=0.6,
                    label="Low contrast",
                    description=f"Text in {element.element_id} may have poor contrast"
                ))

    async def _generate_suggested_moves(self, overlay: LayoutOverlay, actions: List[OptimizationAction]):
        """Generate overlays for suggested element moves."""
        move_actions = [a for a in actions if a.action_type == OptimizationActionType.MOVE_ELEMENT]

        for action in move_actions:
            if 'x' in action.params and 'y' in action.params:
                # Create arrow from current to suggested position
                # This is a simplified representation
                overlay.add_overlay(OverlayElement(
                    overlay_type=OverlayType.SUGGESTED_MOVES,
                    x=action.params['x'],
                    y=action.params['y'],
                    width=20,
                    height=20,
                    color=self.default_colors[OverlayType.SUGGESTED_MOVES],
                    opacity=0.7,
                    label="Move here",
                    description=f"Suggested position for {action.element_id}",
                    metadata={'action': action.description}
                ))

    async def _generate_size_suggestions(self, overlay: LayoutOverlay, actions: List[OptimizationAction]):
        """Generate overlays for size suggestions."""
        resize_actions = [a for a in actions if a.action_type == OptimizationActionType.RESIZE_ELEMENT]

        for action in resize_actions:
            # Would need to calculate suggested bounding box
            # This is a placeholder
            overlay.add_overlay(OverlayElement(
                overlay_type=OverlayType.SIZE_SUGGESTIONS,
                x=0,  # Would be calculated
                y=0,
                width=50,
                height=50,
                color=self.default_colors[OverlayType.SIZE_SUGGESTIONS],
                opacity=0.5,
                label="Resize",
                description=f"Size suggestion for {action.element_id}",
                metadata={'action': action.description}
            ))

    async def _generate_rule_of_thirds(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate rule of thirds grid overlay."""
        third_width = analysis.canvas_width / 3
        third_height = analysis.canvas_height / 3

        # Vertical lines
        for i in [1, 2]:
            x = i * third_width
            overlay.add_overlay(OverlayElement(
                overlay_type=OverlayType.RULE_OF_THIRDS,
                x=x,
                y=0,
                width=0,
                height=analysis.canvas_height,
                color=self.default_colors[OverlayType.RULE_OF_THIRDS],
                opacity=0.4,
                description=f"Rule of thirds vertical line {i}"
            ))

        # Horizontal lines
        for i in [1, 2]:
            y = i * third_height
            overlay.add_overlay(OverlayElement(
                overlay_type=OverlayType.RULE_OF_THIRDS,
                x=0,
                y=y,
                width=analysis.canvas_width,
                height=0,
                color=self.default_colors[OverlayType.RULE_OF_THIRDS],
                opacity=0.4,
                description=f"Rule of thirds horizontal line {i}"
            ))

    async def _generate_golden_ratio(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate golden ratio guides."""
        phi = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

        # Golden ratio divisions
        ratios = [1/phi, 1, phi]

        # Vertical golden ratio lines
        for ratio in ratios:
            if ratio <= 1:
                x = analysis.canvas_width * ratio
                overlay.add_overlay(OverlayElement(
                    overlay_type=OverlayType.GOLDEN_RATIO,
                    x=x,
                    y=0,
                    width=0,
                    height=analysis.canvas_height,
                    color=self.default_colors[OverlayType.GOLDEN_RATIO],
                    opacity=0.3,
                    description=f"Golden ratio vertical line at {ratio:.3f}"
                ))

        # Horizontal golden ratio lines
        for ratio in ratios:
            if ratio <= 1:
                y = analysis.canvas_height * ratio
                overlay.add_overlay(OverlayElement(
                    overlay_type=OverlayType.GOLDEN_RATIO,
                    x=0,
                    y=y,
                    width=analysis.canvas_width,
                    height=0,
                    color=self.default_colors[OverlayType.GOLDEN_RATIO],
                    opacity=0.3,
                    description=f"Golden ratio horizontal line at {ratio:.3f}"
                ))

    async def _generate_visual_hierarchy(self, overlay: LayoutOverlay, analysis: LayoutAnalysis):
        """Generate visual hierarchy indicators."""
        # Show hierarchy levels with different colors/opacity
        hierarchy = analysis.visual_hierarchy

        for i, element_id in enumerate(hierarchy):
            element = next((e for e in analysis.elements if e.element_id == element_id), None)
            if not element:
                continue

            # Higher hierarchy = more prominent indicator
            level = len(hierarchy) - i  # Reverse so higher index = higher hierarchy
            opacity = 0.3 + (level / len(hierarchy)) * 0.4

            overlay.add_overlay(OverlayElement(
                overlay_type=OverlayType.VISUAL_HIERARCHY,
                x=element.bounding_box.x - 3,
                y=element.bounding_box.y - 3,
                width=element.bounding_box.width + 6,
                height=element.bounding_box.height + 6,
                color=self.default_colors[OverlayType.VISUAL_HIERARCHY],
                opacity=opacity,
                label=str(level),
                description=f"Hierarchy level {level} for {element_id}"
            ))

    def set_overlay_color(self, overlay_type: OverlayType, color: str):
        """Set color for a specific overlay type."""
        self.default_colors[overlay_type] = color

    def get_overlay_colors(self) -> Dict[str, str]:
        """Get current overlay colors."""
        return {t.value: c for t, c in self.default_colors.items()}