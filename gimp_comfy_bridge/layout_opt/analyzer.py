"""
Layout Analysis Engine for Comfy Gimpy Studio.

Analyzes template layouts to extract visual elements, properties, and quality metrics.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import math

from ..shared.config import Config

logger = logging.getLogger(__name__)


class ElementType(Enum):
    """Types of layout elements."""
    TEXT = "text"
    IMAGE = "image"
    SHAPE = "shape"
    BACKGROUND = "background"
    DECORATIVE = "decorative"


class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFIED = "justified"


@dataclass
class BoundingBox:
    """Represents a rectangular bounding box."""
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        """Calculate area of bounding box."""
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounding box."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)."""
        return self.width / self.height if self.height > 0 else 0

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box overlaps with another."""
        return not (self.x + self.width <= other.x or
                   other.x + other.width <= self.x or
                   self.y + self.height <= other.y or
                   other.y + other.height <= self.y)

    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate distance between centers of bounding boxes."""
        x1, y1 = self.center
        x2, y2 = other.center
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


@dataclass
class LayoutElement:
    """Represents a single element in the layout."""
    element_id: str
    element_type: ElementType
    bounding_box: BoundingBox
    z_index: int = 0
    opacity: float = 1.0
    visible: bool = True

    # Text-specific properties
    text_content: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None
    text_color: Optional[str] = None
    text_alignment: Optional[TextAlignment] = None
    line_height: Optional[float] = None

    # Image/shape properties
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    stroke_width: Optional[float] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ColorUsage:
    """Tracks color usage in the layout."""
    color: str
    usage_count: int = 0
    elements: List[str] = field(default_factory=list)
    is_brand_color: bool = False


@dataclass
class SpacingAnalysis:
    """Analysis of spacing between elements."""
    horizontal_spacing: List[float] = field(default_factory=list)
    vertical_spacing: List[float] = field(default_factory=list)
    average_horizontal: float = 0.0
    average_vertical: float = 0.0
    min_horizontal: float = float('inf')
    min_vertical: float = float('inf')
    max_horizontal: float = 0.0
    max_vertical: float = 0.0


@dataclass
class LayoutAnalysis:
    """Complete analysis of a layout."""
    canvas_width: float
    canvas_height: float
    elements: List[LayoutElement] = field(default_factory=list)
    color_usage: List[ColorUsage] = field(default_factory=list)
    spacing: SpacingAnalysis = field(default_factory=SpacingAnalysis)
    dominant_colors: List[str] = field(default_factory=list)
    text_elements: List[LayoutElement] = field(default_factory=list)
    visual_hierarchy: List[str] = field(default_factory=list)  # Element IDs in hierarchy order

    # Quality metrics
    text_readability_score: float = 0.0
    color_contrast_score: float = 0.0
    alignment_score: float = 0.0
    spacing_consistency_score: float = 0.0
    visual_balance_score: float = 0.0

    # Metadata
    analysis_timestamp: Optional[float] = None
    source_file: Optional[str] = None


class LayoutAnalyzer:
    """Analyzes layout quality and extracts visual elements."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._gimp_available = self._check_gimp_availability()

    def _check_gimp_availability(self) -> bool:
        """Check if GIMP libraries are available."""
        try:
            import gimp
            return True
        except ImportError:
            return False

    async def analyze_layout(self, template_data: Dict[str, Any]) -> LayoutAnalysis:
        """
        Analyze a layout from template data.

        Args:
            template_data: Template data containing layout information

        Returns:
            LayoutAnalysis with extracted elements and metrics
        """
        logger.info("Starting layout analysis")

        # Extract basic canvas information
        canvas_info = template_data.get('canvas', {})
        canvas_width = canvas_info.get('width', 1920)
        canvas_height = canvas_info.get('height', 1080)

        analysis = LayoutAnalysis(
            canvas_width=float(canvas_width),
            canvas_height=float(canvas_height)
        )

        # Extract elements from template
        elements_data = template_data.get('elements', [])
        elements = []

        for elem_data in elements_data:
            element = self._parse_element(elem_data)
            if element:
                elements.append(element)

        analysis.elements = elements

        # Perform detailed analysis
        await self._analyze_elements(analysis)
        await self._analyze_colors(analysis)
        await self._analyze_spacing(analysis)
        await self._calculate_quality_metrics(analysis)

        logger.info(f"Layout analysis complete: {len(elements)} elements analyzed")
        return analysis

    async def analyze_xcf_file(self, xcf_path: Union[str, Path]) -> LayoutAnalysis:
        """
        Analyze a layout from an XCF file.

        Args:
            xcf_path: Path to XCF file

        Returns:
            LayoutAnalysis with extracted elements and metrics
        """
        if not self._gimp_available:
            raise RuntimeError("GIMP libraries not available for XCF analysis")

        logger.info(f"Analyzing XCF file: {xcf_path}")

        # This would use GIMP's Python API to analyze the XCF file
        # For now, return a mock analysis
        analysis = LayoutAnalysis(
            canvas_width=1920,
            canvas_height=1080,
            source_file=str(xcf_path)
        )

        # TODO: Implement actual XCF parsing using GIMP API
        # analysis.elements = self._extract_layers_from_xcf(xcf_path)

        logger.warning("XCF analysis not yet implemented - returning empty analysis")
        return analysis

    def _parse_element(self, elem_data: Dict[str, Any]) -> Optional[LayoutElement]:
        """Parse element data into LayoutElement."""
        try:
            # Extract bounding box
            bounds = elem_data.get('bounds', {})
            bbox = BoundingBox(
                x=float(bounds.get('x', 0)),
                y=float(bounds.get('y', 0)),
                width=float(bounds.get('width', 100)),
                height=float(bounds.get('height', 50))
            )

            # Determine element type
            elem_type_str = elem_data.get('type', 'shape').lower()
            try:
                elem_type = ElementType(elem_type_str)
            except ValueError:
                elem_type = ElementType.SHAPE

            # Create element
            element = LayoutElement(
                element_id=elem_data.get('id', f"elem_{len(self._current_elements) if hasattr(self, '_current_elements') else 0}"),
                element_type=elem_type,
                bounding_box=bbox,
                z_index=elem_data.get('z_index', 0),
                opacity=elem_data.get('opacity', 1.0),
                visible=elem_data.get('visible', True)
            )

            # Add type-specific properties
            if elem_type == ElementType.TEXT:
                element.text_content = elem_data.get('text', '')
                element.font_family = elem_data.get('font_family')
                element.font_size = elem_data.get('font_size')
                element.font_weight = elem_data.get('font_weight')
                element.text_color = elem_data.get('text_color')
                element.line_height = elem_data.get('line_height')

                # Parse text alignment
                alignment_str = elem_data.get('text_alignment', '').lower()
                try:
                    element.text_alignment = TextAlignment(alignment_str)
                except ValueError:
                    element.text_alignment = TextAlignment.LEFT

            elif elem_type in [ElementType.IMAGE, ElementType.SHAPE]:
                element.fill_color = elem_data.get('fill_color')
                element.stroke_color = elem_data.get('stroke_color')
                element.stroke_width = elem_data.get('stroke_width')

            return element

        except Exception as e:
            logger.warning(f"Failed to parse element: {e}")
            return None

    async def _analyze_elements(self, analysis: LayoutAnalysis) -> None:
        """Analyze individual elements and their properties."""
        # Separate text elements
        analysis.text_elements = [
            elem for elem in analysis.elements
            if elem.element_type == ElementType.TEXT
        ]

        # Calculate visual hierarchy (simple z-index based)
        analysis.visual_hierarchy = sorted(
            [elem.element_id for elem in analysis.elements],
            key=lambda eid: next((e.z_index for e in analysis.elements if e.element_id == eid), 0)
        )

    async def _analyze_colors(self, analysis: LayoutAnalysis) -> None:
        """Analyze color usage in the layout."""
        color_counts: Dict[str, ColorUsage] = {}

        for element in analysis.elements:
            colors_to_check = []

            # Add element-specific colors
            if element.text_color:
                colors_to_check.append(element.text_color)
            if element.fill_color:
                colors_to_check.append(element.fill_color)
            if element.stroke_color:
                colors_to_check.append(element.stroke_color)

            for color in colors_to_check:
                if color not in color_counts:
                    color_counts[color] = ColorUsage(color=color)
                color_counts[color].usage_count += 1
                color_counts[color].elements.append(element.element_id)

        analysis.color_usage = list(color_counts.values())

        # Sort by usage count
        analysis.color_usage.sort(key=lambda cu: cu.usage_count, reverse=True)

        # Extract dominant colors (top 5)
        analysis.dominant_colors = [
            cu.color for cu in analysis.color_usage[:5]
        ]

    async def _analyze_spacing(self, analysis: LayoutAnalysis) -> None:
        """Analyze spacing between elements."""
        if len(analysis.elements) < 2:
            return

        horizontal_spacings = []
        vertical_spacings = []

        # Sort elements by position
        sorted_x = sorted(analysis.elements, key=lambda e: e.bounding_box.x)
        sorted_y = sorted(analysis.elements, key=lambda e: e.bounding_box.y)

        # Calculate horizontal spacings
        for i in range(len(sorted_x) - 1):
            elem1 = sorted_x[i]
            elem2 = sorted_x[i + 1]

            # Only consider non-overlapping elements
            if not elem1.bounding_box.overlaps(elem2.bounding_box):
                spacing = elem2.bounding_box.x - (elem1.bounding_box.x + elem1.bounding_box.width)
                if spacing > 0:
                    horizontal_spacings.append(spacing)

        # Calculate vertical spacings
        for i in range(len(sorted_y) - 1):
            elem1 = sorted_y[i]
            elem2 = sorted_y[i + 1]

            if not elem1.bounding_box.overlaps(elem2.bounding_box):
                spacing = elem2.bounding_box.y - (elem1.bounding_box.y + elem1.bounding_box.height)
                if spacing > 0:
                    vertical_spacings.append(spacing)

        # Calculate statistics
        analysis.spacing.horizontal_spacing = horizontal_spacings
        analysis.spacing.vertical_spacing = vertical_spacings

        if horizontal_spacings:
            analysis.spacing.average_horizontal = sum(horizontal_spacings) / len(horizontal_spacings)
            analysis.spacing.min_horizontal = min(horizontal_spacings)
            analysis.spacing.max_horizontal = max(horizontal_spacings)

        if vertical_spacings:
            analysis.spacing.average_vertical = sum(vertical_spacings) / len(vertical_spacings)
            analysis.spacing.min_vertical = min(vertical_spacings)
            analysis.spacing.max_vertical = max(vertical_spacings)

    async def _calculate_quality_metrics(self, analysis: LayoutAnalysis) -> None:
        """Calculate overall quality metrics for the layout."""
        # Text readability score (based on font size, contrast, etc.)
        analysis.text_readability_score = self._calculate_text_readability(analysis)

        # Color contrast score
        analysis.color_contrast_score = self._calculate_color_contrast(analysis)

        # Alignment score
        analysis.alignment_score = self._calculate_alignment_score(analysis)

        # Spacing consistency score
        analysis.spacing_consistency_score = self._calculate_spacing_consistency(analysis)

        # Visual balance score
        analysis.visual_balance_score = self._calculate_visual_balance(analysis)

    def _calculate_text_readability(self, analysis: LayoutAnalysis) -> float:
        """Calculate text readability score (0-1)."""
        if not analysis.text_elements:
            return 1.0  # No text = perfect readability

        score = 0.0
        for elem in analysis.text_elements:
            elem_score = 0.0

            # Font size factor (larger = better readability)
            if elem.font_size:
                if elem.font_size >= 24:
                    elem_score += 0.4
                elif elem.font_size >= 16:
                    elem_score += 0.3
                elif elem.font_size >= 12:
                    elem_score += 0.2
                else:
                    elem_score += 0.1

            # Contrast factor (would need color analysis)
            elem_score += 0.3  # Placeholder

            # Line height factor
            if elem.line_height and elem.font_size:
                ratio = elem.line_height / elem.font_size
                if 1.2 <= ratio <= 1.8:
                    elem_score += 0.3
                else:
                    elem_score += 0.1

            score += elem_score

        return min(1.0, score / len(analysis.text_elements))

    def _calculate_color_contrast(self, analysis: LayoutAnalysis) -> float:
        """Calculate color contrast score (0-1)."""
        # Simple implementation - more colors = potentially better contrast
        color_count = len(analysis.dominant_colors)
        return min(1.0, color_count / 5.0)  # Max score at 5+ colors

    def _calculate_alignment_score(self, analysis: LayoutAnalysis) -> float:
        """Calculate alignment consistency score (0-1)."""
        if len(analysis.elements) < 2:
            return 1.0

        # Check for common alignment patterns
        left_aligned = sum(1 for e in analysis.elements if abs(e.bounding_box.x) < 10)
        center_aligned = sum(1 for e in analysis.elements
                           if abs(e.bounding_box.center[0] - analysis.canvas_width / 2) < 10)
        right_aligned = sum(1 for e in analysis.elements
                          if abs((e.bounding_box.x + e.bounding_box.width) - analysis.canvas_width) < 10)

        max_aligned = max(left_aligned, center_aligned, right_aligned)
        return min(1.0, max_aligned / len(analysis.elements))

    def _calculate_spacing_consistency(self, analysis: LayoutAnalysis) -> float:
        """Calculate spacing consistency score (0-1)."""
        h_spacings = analysis.spacing.horizontal_spacing
        v_spacings = analysis.spacing.vertical_spacing

        if not h_spacings and not v_spacings:
            return 1.0

        # Calculate coefficient of variation (lower = more consistent)
        def coefficient_of_variation(values):
            if not values:
                return 0
            mean = sum(values) / len(values)
            if mean == 0:
                return 0
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = math.sqrt(variance)
            return std_dev / mean if mean > 0 else 0

        h_cv = coefficient_of_variation(h_spacings)
        v_cv = coefficient_of_variation(v_spacings)

        # Convert CV to score (lower CV = higher score)
        avg_cv = (h_cv + v_cv) / 2 if h_cv > 0 or v_cv > 0 else 0
        return max(0.0, 1.0 - avg_cv)

    def _calculate_visual_balance(self, analysis: LayoutAnalysis) -> float:
        """Calculate visual balance score (0-1)."""
        if len(analysis.elements) < 2:
            return 1.0

        # Calculate center of mass
        total_area = sum(e.bounding_box.area for e in analysis.elements)
        if total_area == 0:
            return 0.5

        center_x = sum(e.bounding_box.center[0] * e.bounding_box.area for e in analysis.elements) / total_area
        center_y = sum(e.bounding_box.center[1] * e.bounding_box.area for e in analysis.elements) / total_area

        canvas_center_x = analysis.canvas_width / 2
        canvas_center_y = analysis.canvas_height / 2

        # Distance from canvas center (normalized)
        distance = math.sqrt((center_x - canvas_center_x) ** 2 + (center_y - canvas_center_y) ** 2)
        max_distance = math.sqrt(canvas_center_x ** 2 + canvas_center_y ** 2)

        # Closer to center = higher score
        return max(0.0, 1.0 - (distance / max_distance))