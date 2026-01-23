"""
Layout Optimization Engine for Comfy Gimpy Studio.

Generates optimization actions to improve layout quality.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import math
import copy

from .analyzer import LayoutAnalysis, LayoutElement, BoundingBox
from .scorer import LayoutScore, ScoreDimension
from .heuristics import RuleViolation, RuleSeverity

logger = logging.getLogger(__name__)


class OptimizationActionType(Enum):
    """Types of optimization actions."""
    MOVE_ELEMENT = "move_element"
    RESIZE_ELEMENT = "resize_element"
    ADJUST_SPACING = "adjust_spacing"
    CHANGE_COLOR = "change_color"
    CHANGE_FONT = "change_font"
    ALIGN_ELEMENTS = "align_elements"
    REORDER_HIERARCHY = "reorder_hierarchy"
    ADD_ELEMENT = "add_element"
    REMOVE_ELEMENT = "remove_element"


@dataclass
class OptimizationAction:
    """Represents a single optimization action."""
    action_type: OptimizationActionType
    element_id: Optional[str]
    description: str
    confidence: float = 1.0

    # Action-specific parameters
    params: Dict[str, Any] = field(default_factory=dict)

    # Expected impact
    expected_improvement: float = 0.0  # Expected score improvement (0-1)

    def apply_to_analysis(self, analysis: LayoutAnalysis) -> LayoutAnalysis:
        """Apply this action to a layout analysis (simulation)."""
        # Create a copy of the analysis
        new_analysis = copy.deepcopy(analysis)

        if self.action_type == OptimizationActionType.MOVE_ELEMENT:
            self._apply_move_element(new_analysis)
        elif self.action_type == OptimizationActionType.RESIZE_ELEMENT:
            self._apply_resize_element(new_analysis)
        elif self.action_type == OptimizationActionType.ADJUST_SPACING:
            self._apply_adjust_spacing(new_analysis)
        elif self.action_type == OptimizationActionType.CHANGE_COLOR:
            self._apply_change_color(new_analysis)
        elif self.action_type == OptimizationActionType.CHANGE_FONT:
            self._apply_change_font(new_analysis)
        elif self.action_type == OptimizationActionType.ALIGN_ELEMENTS:
            self._apply_align_elements(new_analysis)
        elif self.action_type == OptimizationActionType.REORDER_HIERARCHY:
            self._apply_reorder_hierarchy(new_analysis)

        return new_analysis

    def _apply_move_element(self, analysis: LayoutAnalysis):
        """Apply move element action."""
        element = next((e for e in analysis.elements if e.element_id == self.element_id), None)
        if element and 'x' in self.params and 'y' in self.params:
            element.bounding_box.x = self.params['x']
            element.bounding_box.y = self.params['y']

    def _apply_resize_element(self, analysis: LayoutAnalysis):
        """Apply resize element action."""
        element = next((e for e in analysis.elements if e.element_id == self.element_id), None)
        if element:
            if 'width' in self.params:
                element.bounding_box.width = self.params['width']
            if 'height' in self.params:
                element.bounding_box.height = self.params['height']

    def _apply_adjust_spacing(self, analysis: LayoutAnalysis):
        """Apply spacing adjustment action."""
        # This would adjust spacing between elements
        # Implementation depends on specific spacing logic
        pass

    def _apply_change_color(self, analysis: LayoutAnalysis):
        """Apply color change action."""
        element = next((e for e in analysis.elements if e.element_id == self.element_id), None)
        if element and 'color' in self.params:
            if element.element_type.name == 'TEXT':
                element.text_color = self.params['color']
            else:
                element.fill_color = self.params['color']

    def _apply_change_font(self, analysis: LayoutAnalysis):
        """Apply font change action."""
        element = next((e for e in analysis.elements if e.element_id == self.element_id), None)
        if element and element.element_type.name == 'TEXT':
            if 'font_size' in self.params:
                element.font_size = self.params['font_size']
            if 'font_family' in self.params:
                element.font_family = self.params['font_family']

    def _apply_align_elements(self, analysis: LayoutAnalysis):
        """Apply element alignment action."""
        # Implementation would align multiple elements
        pass

    def _apply_reorder_hierarchy(self, analysis: LayoutAnalysis):
        """Apply hierarchy reordering action."""
        if 'new_order' in self.params:
            analysis.visual_hierarchy = self.params['new_order']


@dataclass
class OptimizationResult:
    """Result of layout optimization."""
    original_score: float
    optimized_score: float
    improvement: float
    actions: List[OptimizationAction]
    optimized_analysis: LayoutAnalysis

    @property
    def score_improvement(self) -> float:
        """Get the score improvement percentage."""
        if self.original_score == 0:
            return 0.0
        return (self.optimized_score - self.original_score) / self.original_score


class LayoutOptimizer:
    """Optimizes layouts by generating improvement actions."""

    def __init__(self):
        self.max_actions = 10  # Maximum actions to suggest
        self.min_confidence = 0.5  # Minimum confidence for actions

    async def optimize_layout(self, analysis: LayoutAnalysis,
                            score: Optional[LayoutScore] = None) -> OptimizationResult:
        """
        Optimize a layout by generating improvement actions.

        Args:
            analysis: Layout analysis to optimize
            score: Optional pre-computed layout score

        Returns:
            OptimizationResult with suggested actions
        """
        logger.info("Starting layout optimization")

        original_score = score.overall_score if score else 0.0

        # Generate optimization actions
        actions = await self._generate_actions(analysis, score)

        # Apply actions to create optimized analysis
        optimized_analysis = await self._apply_actions(analysis, actions)

        # Calculate optimized score (would need scorer)
        optimized_score = original_score + sum(action.expected_improvement for action in actions)
        optimized_score = min(1.0, optimized_score)  # Cap at 1.0

        improvement = optimized_score - original_score

        result = OptimizationResult(
            original_score=original_score,
            optimized_score=optimized_score,
            improvement=improvement,
            actions=actions,
            optimized_analysis=optimized_analysis
        )

        logger.info(f"Layout optimization complete: {len(actions)} actions, improvement: {improvement:.3f}")
        return result

    async def _generate_actions(self, analysis: LayoutAnalysis,
                              score: Optional[LayoutScore]) -> List[OptimizationAction]:
        """Generate optimization actions based on analysis and score."""
        actions = []

        # Generate actions from rule violations
        if score:
            violation_actions = await self._generate_violation_actions(analysis, score.violations)
            actions.extend(violation_actions)

        # Generate actions from low-scoring dimensions
        if score:
            dimension_actions = await self._generate_dimension_actions(analysis, score)
            actions.extend(dimension_actions)

        # Generate general improvement actions
        general_actions = await self._generate_general_actions(analysis)
        actions.extend(general_actions)

        # Sort by expected improvement and confidence
        actions.sort(key=lambda a: (a.expected_improvement, a.confidence), reverse=True)

        # Limit to max actions
        actions = actions[:self.max_actions]

        # Filter by minimum confidence
        actions = [a for a in actions if a.confidence >= self.min_confidence]

        return actions

    async def _generate_violation_actions(self, analysis: LayoutAnalysis,
                                        violations: List[RuleViolation]) -> List[OptimizationAction]:
        """Generate actions to fix rule violations."""
        actions = []

        for violation in violations:
            action = await self._create_action_from_violation(violation, analysis)
            if action:
                actions.append(action)

        return actions

    async def _create_action_from_violation(self, violation: RuleViolation,
                                          analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create an optimization action from a rule violation."""
        element = None
        if violation.element_id:
            element = next((e for e in analysis.elements if e.element_id == violation.element_id), None)

        # Create action based on violation type
        if 'contrast' in violation.message.lower():
            return self._create_contrast_action(violation, element)
        elif 'alignment' in violation.message.lower():
            return self._create_alignment_action(violation, analysis)
        elif 'spacing' in violation.message.lower():
            return self._create_spacing_action(violation, analysis)
        elif 'hierarchy' in violation.message.lower():
            return self._create_hierarchy_action(violation, element, analysis)
        elif 'balance' in violation.message.lower():
            return self._create_balance_action(violation, analysis)
        elif 'harmony' in violation.message.lower():
            return self._create_harmony_action(violation, analysis)
        elif 'readability' in violation.message.lower():
            return self._create_readability_action(violation, element)

        return None

    def _create_contrast_action(self, violation: RuleViolation,
                              element: Optional[LayoutElement]) -> Optional[OptimizationAction]:
        """Create action to fix contrast issues."""
        if not element:
            return None

        return OptimizationAction(
            action_type=OptimizationActionType.CHANGE_COLOR,
            element_id=element.element_id,
            description="Improve text contrast for better readability",
            confidence=0.8,
            params={'color': '#000000'},  # Would need smarter color selection
            expected_improvement=0.1
        )

    def _create_alignment_action(self, violation: RuleViolation,
                               analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create action to fix alignment issues."""
        # Find elements that could be aligned
        elements = analysis.elements
        if len(elements) < 2:
            return None

        # Simple alignment to left edge
        left_edge = min(e.bounding_box.x for e in elements)

        return OptimizationAction(
            action_type=OptimizationActionType.ALIGN_ELEMENTS,
            element_id=None,
            description="Align elements to common left edge",
            confidence=0.7,
            params={'alignment': 'left', 'position': left_edge},
            expected_improvement=0.05
        )

    def _create_spacing_action(self, violation: RuleViolation,
                             analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create action to fix spacing issues."""
        return OptimizationAction(
            action_type=OptimizationActionType.ADJUST_SPACING,
            element_id=None,
            description="Standardize spacing between elements",
            confidence=0.6,
            params={'target_spacing': 20},  # Standard spacing
            expected_improvement=0.03
        )

    def _create_hierarchy_action(self, violation: RuleViolation,
                               element: Optional[LayoutElement],
                               analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create action to fix hierarchy issues."""
        if not element:
            return None

        # Suggest size adjustment based on hierarchy position
        hierarchy_index = analysis.visual_hierarchy.index(element.element_id) if element.element_id in analysis.visual_hierarchy else 0
        target_size_factor = 1.0 - (hierarchy_index / len(analysis.visual_hierarchy))

        current_area = element.bounding_box.area
        target_area = current_area * target_size_factor

        # Maintain aspect ratio
        aspect_ratio = element.bounding_box.aspect_ratio
        new_width = math.sqrt(target_area * aspect_ratio)
        new_height = new_width / aspect_ratio

        return OptimizationAction(
            action_type=OptimizationActionType.RESIZE_ELEMENT,
            element_id=element.element_id,
            description="Adjust element size to match hierarchy position",
            confidence=0.7,
            params={'width': new_width, 'height': new_height},
            expected_improvement=0.04
        )

    def _create_balance_action(self, violation: RuleViolation,
                             analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create action to fix balance issues."""
        # Calculate center of mass
        total_area = sum(e.bounding_box.area * e.opacity for e in analysis.elements)
        if total_area == 0:
            return None

        center_x = sum(e.bounding_box.center[0] * e.bounding_box.area * e.opacity for e in analysis.elements) / total_area
        center_y = sum(e.bounding_box.center[1] * e.bounding_box.area * e.opacity for e in analysis.elements) / total_area

        canvas_center_x = analysis.canvas_width / 2
        canvas_center_y = analysis.canvas_height / 2

        # Find element farthest from center to move
        farthest_element = max(
            analysis.elements,
            key=lambda e: math.sqrt((e.bounding_box.center[0] - canvas_center_x) ** 2 +
                                   (e.bounding_box.center[1] - canvas_center_y) ** 2)
        )

        # Suggest moving toward center
        move_x = (canvas_center_x - farthest_element.bounding_box.center[0]) * 0.3
        move_y = (canvas_center_y - farthest_element.bounding_box.center[1]) * 0.3

        new_x = farthest_element.bounding_box.x + move_x
        new_y = farthest_element.bounding_box.y + move_y

        return OptimizationAction(
            action_type=OptimizationActionType.MOVE_ELEMENT,
            element_id=farthest_element.element_id,
            description="Move element toward center for better balance",
            confidence=0.6,
            params={'x': new_x, 'y': new_y},
            expected_improvement=0.06
        )

    def _create_harmony_action(self, violation: RuleViolation,
                             analysis: LayoutAnalysis) -> Optional[OptimizationAction]:
        """Create action to fix color harmony issues."""
        if len(analysis.dominant_colors) <= 3:
            return None  # Already good

        # Suggest removing least used color
        if analysis.color_usage:
            least_used = min(analysis.color_usage, key=lambda cu: cu.usage_count)
            # This would need to find elements using this color and suggest alternatives
            return OptimizationAction(
                action_type=OptimizationActionType.CHANGE_COLOR,
                element_id=None,  # Would need to specify which element
                description="Simplify color palette for better harmony",
                confidence=0.5,
                params={'old_color': least_used.color},
                expected_improvement=0.02
            )

        return None

    def _create_readability_action(self, violation: RuleViolation,
                                 element: Optional[LayoutElement]) -> Optional[OptimizationAction]:
        """Create action to fix readability issues."""
        if not element or element.element_type.name != 'TEXT':
            return None

        if 'size' in violation.message.lower() and element.font_size:
            new_size = min(element.font_size * 1.2, 24)  # Increase by 20%, max 24pt

            return OptimizationAction(
                action_type=OptimizationActionType.CHANGE_FONT,
                element_id=element.element_id,
                description="Increase font size for better readability",
                confidence=0.9,
                params={'font_size': new_size},
                expected_improvement=0.08
            )

        return None

    async def _generate_dimension_actions(self, analysis: LayoutAnalysis,
                                        score: LayoutScore) -> List[OptimizationAction]:
        """Generate actions based on low-scoring dimensions."""
        actions = []

        # Check each dimension
        for dim, dim_score in score.dimensions.items():
            if dim_score.score < 0.6:  # Below 60%
                dimension_actions = await self._generate_dimension_specific_actions(dim, analysis, dim_score)
                actions.extend(dimension_actions)

        return actions

    async def _generate_dimension_specific_actions(self, dimension: ScoreDimension,
                                                 analysis: LayoutAnalysis,
                                                 dim_score: Any) -> List[OptimizationAction]:
        """Generate actions for a specific low-scoring dimension."""
        actions = []

        if dimension == ScoreDimension.READABILITY:
            actions.extend(await self._generate_readability_actions(analysis))
        elif dimension == ScoreDimension.BALANCE:
            actions.extend(await self._generate_balance_actions(analysis))
        elif dimension == ScoreDimension.ALIGNMENT:
            actions.extend(await self._generate_alignment_actions(analysis))
        elif dimension == ScoreDimension.SPACING:
            actions.extend(await self._generate_spacing_actions(analysis))

        return actions

    async def _generate_readability_actions(self, analysis: LayoutAnalysis) -> List[OptimizationAction]:
        """Generate readability improvement actions."""
        actions = []

        for element in analysis.text_elements:
            if element.font_size and element.font_size < 14:
                actions.append(OptimizationAction(
                    action_type=OptimizationActionType.CHANGE_FONT,
                    element_id=element.element_id,
                    description="Increase font size for better readability",
                    confidence=0.8,
                    params={'font_size': min(element.font_size * 1.3, 18)},
                    expected_improvement=0.05
                ))

        return actions

    async def _generate_balance_actions(self, analysis: LayoutAnalysis) -> List[OptimizationAction]:
        """Generate balance improvement actions."""
        actions = []

        # Simple balance improvement: move elements toward center
        canvas_center_x = analysis.canvas_width / 2

        for element in analysis.elements:
            elem_center_x = element.bounding_box.center[0]
            distance_from_center = abs(elem_center_x - canvas_center_x)

            if distance_from_center > analysis.canvas_width * 0.3:  # More than 30% from center
                move_distance = distance_from_center * 0.2  # Move 20% closer to center
                new_x = element.bounding_box.x + (canvas_center_x - elem_center_x) * 0.2

                actions.append(OptimizationAction(
                    action_type=OptimizationActionType.MOVE_ELEMENT,
                    element_id=element.element_id,
                    description="Move element closer to center for better balance",
                    confidence=0.6,
                    params={'x': new_x, 'y': element.bounding_box.y},
                    expected_improvement=0.03
                ))

        return actions

    async def _generate_alignment_actions(self, analysis: LayoutAnalysis) -> List[OptimizationAction]:
        """Generate alignment improvement actions."""
        actions = []

        if len(analysis.elements) < 3:
            return actions

        # Check for potential alignment opportunities
        left_edges = [e.bounding_box.x for e in analysis.elements]
        min_left = min(left_edges)
        max_left = max(left_edges)

        if max_left - min_left > 50:  # Significant spread
            # Suggest left alignment
            actions.append(OptimizationAction(
                action_type=OptimizationActionType.ALIGN_ELEMENTS,
                element_id=None,
                description="Align elements to common left edge",
                confidence=0.7,
                params={'alignment': 'left', 'position': min_left},
                expected_improvement=0.04
            ))

        return actions

    async def _generate_spacing_actions(self, analysis: LayoutAnalysis) -> List[OptimizationAction]:
        """Generate spacing improvement actions."""
        actions = []

        spacing = analysis.spacing
        if spacing.average_horizontal > 0 and spacing.max_horizontal - spacing.min_horizontal > spacing.average_horizontal:
            actions.append(OptimizationAction(
                action_type=OptimizationActionType.ADJUST_SPACING,
                element_id=None,
                description="Standardize horizontal spacing between elements",
                confidence=0.6,
                params={'type': 'horizontal', 'target_spacing': spacing.average_horizontal},
                expected_improvement=0.02
            ))

        return actions

    async def _generate_general_actions(self, analysis: LayoutAnalysis) -> List[OptimizationAction]:
        """Generate general improvement actions."""
        actions = []

        # Rule of thirds alignment suggestions
        third_width = analysis.canvas_width / 3
        third_height = analysis.canvas_height / 3

        for element in analysis.elements[:3]:  # Check first few elements
            center_x, center_y = element.bounding_box.center

            # Check proximity to rule of thirds lines
            near_third = (
                abs(center_x - third_width) < 30 or
                abs(center_x - 2 * third_width) < 30 or
                abs(center_y - third_height) < 30 or
                abs(center_y - 2 * third_height) < 30
            )

            if not near_third:
                # Suggest moving to nearest third
                nearest_x = min([third_width, 2 * third_width],
                              key=lambda x: abs(center_x - x))
                nearest_y = min([third_height, 2 * third_height],
                              key=lambda y: abs(center_y - y))

                actions.append(OptimizationAction(
                    action_type=OptimizationActionType.MOVE_ELEMENT,
                    element_id=element.element_id,
                    description="Move element to align with rule of thirds",
                    confidence=0.5,
                    params={
                        'x': element.bounding_box.x + (nearest_x - center_x),
                        'y': element.bounding_box.y + (nearest_y - center_y)
                    },
                    expected_improvement=0.02
                ))

        return actions

    async def _apply_actions(self, analysis: LayoutAnalysis,
                           actions: List[OptimizationAction]) -> LayoutAnalysis:
        """Apply a list of actions to create optimized analysis."""
        optimized = copy.deepcopy(analysis)

        for action in actions:
            try:
                optimized = action.apply_to_analysis(optimized)
            except Exception as e:
                logger.warning(f"Failed to apply action {action.action_type}: {e}")

        return optimized

    def set_max_actions(self, max_actions: int):
        """Set maximum number of actions to generate."""
        self.max_actions = max(1, max_actions)

    def set_min_confidence(self, min_confidence: float):
        """Set minimum confidence threshold for actions."""
        self.min_confidence = max(0.0, min(1.0, min_confidence))