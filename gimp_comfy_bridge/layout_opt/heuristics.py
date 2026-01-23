"""
Design Heuristics and Rules for Layout Optimization.

Implements various design principles and rules for evaluating and improving layouts.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import math

from .analyzer import LayoutAnalysis, LayoutElement, BoundingBox

logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Severity levels for design rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


class RuleCategory(Enum):
    """Categories of design rules."""
    COMPOSITION = "composition"
    TYPOGRAPHY = "typography"
    COLOR = "color"
    SPACING = "spacing"
    ALIGNMENT = "alignment"
    HIERARCHY = "hierarchy"
    BRAND = "brand"


@dataclass
class DesignRule:
    """Represents a design rule with evaluation logic."""
    rule_id: str
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    evaluator: Callable[[LayoutAnalysis], List[Dict[str, Any]]]
    enabled: bool = True

    def evaluate(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate the rule against a layout analysis."""
        if not self.enabled:
            return []

        try:
            return self.evaluator(analysis)
        except Exception as e:
            logger.warning(f"Rule evaluation failed for {self.rule_id}: {e}")
            return []


@dataclass
class RuleViolation:
    """Represents a rule violation or issue."""
    rule_id: str
    element_id: Optional[str]
    message: str
    severity: RuleSeverity
    category: RuleCategory
    suggestion: str
    confidence: float = 1.0

    # Location information
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class DesignHeuristics:
    """Collection of design rules and heuristics for layout evaluation."""

    def __init__(self):
        self.rules: Dict[str, DesignRule] = {}
        self._initialize_rules()

    def _initialize_rules(self):
        """Initialize all design rules."""
        self._add_composition_rules()
        self._add_typography_rules()
        self._add_color_rules()
        self._add_spacing_rules()
        self._add_alignment_rules()
        self._add_hierarchy_rules()
        self._add_brand_rules()

    def evaluate_all(self, analysis: LayoutAnalysis) -> List[RuleViolation]:
        """Evaluate all enabled rules against the layout."""
        violations = []

        for rule in self.rules.values():
            rule_violations = rule.evaluate(analysis)
            for violation_data in rule_violations:
                violation = RuleViolation(
                    rule_id=rule.rule_id,
                    element_id=violation_data.get('element_id'),
                    message=violation_data.get('message', ''),
                    severity=rule.severity,
                    category=rule.category,
                    suggestion=violation_data.get('suggestion', ''),
                    confidence=violation_data.get('confidence', 1.0),
                    x=violation_data.get('x'),
                    y=violation_data.get('y'),
                    width=violation_data.get('width'),
                    height=violation_data.get('height')
                )
                violations.append(violation)

        return violations

    def get_rule(self, rule_id: str) -> Optional[DesignRule]:
        """Get a specific rule by ID."""
        return self.rules.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a specific rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a specific rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def _add_composition_rules(self):
        """Add composition-related design rules."""
        # Rule of Thirds
        self.rules['rule_of_thirds'] = DesignRule(
            rule_id='rule_of_thirds',
            name='Rule of Thirds',
            description='Important elements should align with rule of thirds grid lines',
            category=RuleCategory.COMPOSITION,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_rule_of_thirds
        )

        # Golden Ratio
        self.rules['golden_ratio'] = DesignRule(
            rule_id='golden_ratio',
            name='Golden Ratio',
            description='Layout proportions should follow the golden ratio (1:1.618)',
            category=RuleCategory.COMPOSITION,
            severity=RuleSeverity.LOW,
            evaluator=self._evaluate_golden_ratio
        )

        # Visual Balance
        self.rules['visual_balance'] = DesignRule(
            rule_id='visual_balance',
            name='Visual Balance',
            description='Layout should have balanced visual weight distribution',
            category=RuleCategory.COMPOSITION,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_visual_balance
        )

    def _add_typography_rules(self):
        """Add typography-related design rules."""
        # Font Size Hierarchy
        self.rules['font_hierarchy'] = DesignRule(
            rule_id='font_hierarchy',
            name='Font Size Hierarchy',
            description='Text elements should have clear size hierarchy',
            category=RuleCategory.TYPOGRAPHY,
            severity=RuleSeverity.HIGH,
            evaluator=self._evaluate_font_hierarchy
        )

        # Text Contrast
        self.rules['text_contrast'] = DesignRule(
            rule_id='text_contrast',
            name='Text Contrast',
            description='Text should have sufficient contrast with background',
            category=RuleCategory.TYPOGRAPHY,
            severity=RuleSeverity.CRITICAL,
            evaluator=self._evaluate_text_contrast
        )

        # Line Length
        self.rules['line_length'] = DesignRule(
            rule_id='line_length',
            name='Line Length',
            description='Text lines should be appropriate length for readability',
            category=RuleCategory.TYPOGRAPHY,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_line_length
        )

    def _add_color_rules(self):
        """Add color-related design rules."""
        # Color Harmony
        self.rules['color_harmony'] = DesignRule(
            rule_id='color_harmony',
            name='Color Harmony',
            description='Colors should work well together',
            category=RuleCategory.COLOR,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_color_harmony
        )

        # Color Contrast
        self.rules['color_contrast'] = DesignRule(
            rule_id='color_contrast',
            name='Color Contrast',
            description='Elements should have sufficient color contrast',
            category=RuleCategory.COLOR,
            severity=RuleSeverity.HIGH,
            evaluator=self._evaluate_color_contrast
        )

    def _add_spacing_rules(self):
        """Add spacing-related design rules."""
        # Consistent Spacing
        self.rules['consistent_spacing'] = DesignRule(
            rule_id='consistent_spacing',
            name='Consistent Spacing',
            description='Spacing between elements should be consistent',
            category=RuleCategory.SPACING,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_consistent_spacing
        )

        # White Space
        self.rules['white_space'] = DesignRule(
            rule_id='white_space',
            name='White Space',
            description='Layout should have appropriate white space',
            category=RuleCategory.SPACING,
            severity=RuleSeverity.LOW,
            evaluator=self._evaluate_white_space
        )

    def _add_alignment_rules(self):
        """Add alignment-related design rules."""
        # Element Alignment
        self.rules['element_alignment'] = DesignRule(
            rule_id='element_alignment',
            name='Element Alignment',
            description='Elements should be properly aligned',
            category=RuleCategory.ALIGNMENT,
            severity=RuleSeverity.MEDIUM,
            evaluator=self._evaluate_element_alignment
        )

    def _add_hierarchy_rules(self):
        """Add hierarchy-related design rules."""
        # Visual Hierarchy
        self.rules['visual_hierarchy'] = DesignRule(
            rule_id='visual_hierarchy',
            name='Visual Hierarchy',
            description='Elements should have clear visual hierarchy',
            category=RuleCategory.HIERARCHY,
            severity=RuleSeverity.HIGH,
            evaluator=self._evaluate_visual_hierarchy
        )

    def _add_brand_rules(self):
        """Add brand-related design rules."""
        # Brand Color Usage
        self.rules['brand_colors'] = DesignRule(
            rule_id='brand_colors',
            name='Brand Colors',
            description='Layout should use brand colors appropriately',
            category=RuleCategory.BRAND,
            severity=RuleSeverity.HIGH,
            evaluator=self._evaluate_brand_colors
        )

        # Brand Typography
        self.rules['brand_typography'] = DesignRule(
            rule_id='brand_typography',
            name='Brand Typography',
            description='Text should follow brand typography guidelines',
            category=RuleCategory.BRAND,
            severity=RuleSeverity.HIGH,
            evaluator=self._evaluate_brand_typography
        )

    # Rule evaluation methods

    def _evaluate_rule_of_thirds(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate rule of thirds compliance."""
        violations = []

        # Calculate rule of thirds lines
        third_width = analysis.canvas_width / 3
        third_height = analysis.canvas_height / 3

        rule_lines = {
            'vertical': [third_width, 2 * third_width],
            'horizontal': [third_height, 2 * third_height]
        }

        for element in analysis.elements:
            bbox = element.bounding_box
            center_x, center_y = bbox.center

            # Check if element center is near rule of thirds lines
            near_vertical = any(abs(center_x - line) < 50 for line in rule_lines['vertical'])
            near_horizontal = any(abs(center_y - line) < 50 for line in rule_lines['horizontal'])

            if not (near_vertical or near_horizontal):
                violations.append({
                    'element_id': element.element_id,
                    'message': f'Element {element.element_id} not aligned with rule of thirds',
                    'suggestion': 'Move element to align with rule of thirds grid lines',
                    'x': bbox.x,
                    'y': bbox.y,
                    'width': bbox.width,
                    'height': bbox.height,
                    'confidence': 0.7
                })

        return violations

    def _evaluate_golden_ratio(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate golden ratio proportions."""
        violations = []
        phi = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

        for element in analysis.elements:
            bbox = element.bounding_box
            ratio = bbox.aspect_ratio

            # Check if ratio is close to golden ratio or its inverse
            if not (0.5 < ratio < 2.0):  # Skip very extreme ratios
                golden_diff = min(abs(ratio - phi), abs(ratio - 1/phi))
                if golden_diff > 0.3:  # Not close to golden ratio
                    violations.append({
                        'element_id': element.element_id,
                        'message': f'Element {element.element_id} aspect ratio ({ratio:.2f}) not following golden ratio',
                        'suggestion': 'Adjust element dimensions to follow golden ratio proportions',
                        'x': bbox.x,
                        'y': bbox.y,
                        'width': bbox.width,
                        'height': bbox.height,
                        'confidence': 0.5
                    })

        return violations

    def _evaluate_visual_balance(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate visual balance."""
        violations = []

        if len(analysis.elements) < 2:
            return violations

        # Calculate visual weight (area * opacity)
        total_weight = sum(elem.bounding_box.area * elem.opacity for elem in analysis.elements)
        if total_weight == 0:
            return violations

        # Calculate center of visual mass
        center_x = sum(elem.bounding_box.center[0] * elem.bounding_box.area * elem.opacity
                      for elem in analysis.elements) / total_weight
        center_y = sum(elem.bounding_box.center[1] * elem.bounding_box.area * elem.opacity
                      for elem in analysis.elements) / total_weight

        canvas_center_x = analysis.canvas_width / 2
        canvas_center_y = analysis.canvas_height / 2

        # Check if center of mass is reasonably close to canvas center
        distance = math.sqrt((center_x - canvas_center_x) ** 2 + (center_y - canvas_center_y) ** 2)
        max_distance = math.sqrt(canvas_center_x ** 2 + canvas_center_y ** 2) / 2

        if distance > max_distance * 0.7:  # More than 70% of max distance
            violations.append({
                'message': f'Layout visual balance is off-center (distance: {distance:.1f}px)',
                'suggestion': 'Adjust element positions or sizes to improve visual balance',
                'confidence': 0.8
            })

        return violations

    def _evaluate_font_hierarchy(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate font size hierarchy."""
        violations = []

        text_elements = [e for e in analysis.elements if e.element_type.name == 'TEXT']
        if len(text_elements) < 2:
            return violations

        font_sizes = []
        for elem in text_elements:
            if elem.font_size:
                font_sizes.append((elem.element_id, elem.font_size))

        if len(font_sizes) < 2:
            return violations

        # Sort by font size
        font_sizes.sort(key=lambda x: x[1], reverse=True)

        # Check for clear hierarchy (significant size differences)
        hierarchy_levels = 1
        prev_size = font_sizes[0][1]

        for _, size in font_sizes[1:]:
            if prev_size / size >= 1.2:  # At least 20% size difference
                hierarchy_levels += 1
                prev_size = size

        if hierarchy_levels < min(3, len(font_sizes)):  # Should have at least 3 levels for multiple elements
            violations.append({
                'message': f'Font hierarchy unclear - only {hierarchy_levels} distinct size levels',
                'suggestion': 'Create clearer font size hierarchy with more distinct size levels',
                'confidence': 0.9
            })

        return violations

    def _evaluate_text_contrast(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate text contrast."""
        violations = []

        for elem in analysis.text_elements:
            # This would need actual color analysis
            # For now, assume good contrast unless we have specific issues
            if elem.font_size and elem.font_size < 12:
                violations.append({
                    'element_id': elem.element_id,
                    'message': f'Text in {elem.element_id} may be too small for good readability',
                    'suggestion': 'Increase font size to at least 12pt for better readability',
                    'x': elem.bounding_box.x,
                    'y': elem.bounding_box.y,
                    'width': elem.bounding_box.width,
                    'height': elem.bounding_box.height,
                    'confidence': 0.8
                })

        return violations

    def _evaluate_line_length(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate text line length."""
        violations = []

        for elem in analysis.text_elements:
            if elem.text_content and elem.bounding_box.width > 0:
                # Estimate characters per line
                avg_char_width = elem.font_size * 0.6 if elem.font_size else 8  # Rough estimate
                chars_per_line = elem.bounding_box.width / avg_char_width

                if chars_per_line > 80:  # Too long for comfortable reading
                    violations.append({
                        'element_id': elem.element_id,
                        'message': f'Text line too long in {elem.element_id} ({chars_per_line:.0f} chars)',
                        'suggestion': 'Shorten text or increase element width for better readability',
                        'x': elem.bounding_box.x,
                        'y': elem.bounding_box.y,
                        'width': elem.bounding_box.width,
                        'height': elem.bounding_box.height,
                        'confidence': 0.7
                    })

        return violations

    def _evaluate_color_harmony(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate color harmony."""
        violations = []

        if len(analysis.dominant_colors) < 2:
            violations.append({
                'message': 'Layout uses very few colors - consider adding more variety',
                'suggestion': 'Add complementary colors to create better visual harmony',
                'confidence': 0.6
            })
        elif len(analysis.dominant_colors) > 6:
            violations.append({
                'message': 'Layout uses too many colors - may appear chaotic',
                'suggestion': 'Reduce color palette to 3-5 main colors for better harmony',
                'confidence': 0.5
            })

        return violations

    def _evaluate_color_contrast(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate color contrast between elements."""
        # Placeholder - would need actual color analysis
        return []

    def _evaluate_consistent_spacing(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate spacing consistency."""
        violations = []

        spacing = analysis.spacing
        if spacing.average_horizontal > 0:
            h_variation = spacing.max_horizontal - spacing.min_horizontal
            if h_variation > spacing.average_horizontal * 0.5:  # More than 50% variation
                violations.append({
                    'message': f'Inconsistent horizontal spacing (variation: {h_variation:.1f}px)',
                    'suggestion': 'Standardize horizontal spacing between elements',
                    'confidence': 0.7
                })

        if spacing.average_vertical > 0:
            v_variation = spacing.max_vertical - spacing.min_vertical
            if v_variation > spacing.average_vertical * 0.5:
                violations.append({
                    'message': f'Inconsistent vertical spacing (variation: {v_variation:.1f}px)',
                    'suggestion': 'Standardize vertical spacing between elements',
                    'confidence': 0.7
                })

        return violations

    def _evaluate_white_space(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate white space usage."""
        violations = []

        # Calculate total element area
        total_element_area = sum(elem.bounding_box.area for elem in analysis.elements)
        canvas_area = analysis.canvas_width * analysis.canvas_height

        if canvas_area > 0:
            element_ratio = total_element_area / canvas_area

            if element_ratio > 0.8:  # More than 80% filled
                violations.append({
                    'message': f'Layout too crowded ({element_ratio:.1%} filled)',
                    'suggestion': 'Add more white space for better visual breathing room',
                    'confidence': 0.6
                })
            elif element_ratio < 0.3:  # Less than 30% filled
                violations.append({
                    'message': f'Layout too sparse ({element_ratio:.1%} filled)',
                    'suggestion': 'Consider adding more visual elements or increasing element sizes',
                    'confidence': 0.4
                })

        return violations

    def _evaluate_element_alignment(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate element alignment."""
        violations = []

        if len(analysis.elements) < 3:
            return violations

        # Check for common alignment patterns
        left_edges = [elem.bounding_box.x for elem in analysis.elements]
        right_edges = [elem.bounding_box.x + elem.bounding_box.width for elem in analysis.elements]
        centers = [elem.bounding_box.center[0] for elem in analysis.elements]

        # Check if elements are aligned
        left_aligned = len(set(round(x, 0) for x in left_edges)) <= 2  # Allow small tolerance
        right_aligned = len(set(round(x, 0) for x in right_edges)) <= 2
        center_aligned = len(set(round(x, 0) for x in centers)) <= 2

        if not (left_aligned or right_aligned or center_aligned):
            violations.append({
                'message': 'Elements lack consistent alignment',
                'suggestion': 'Align elements to a common edge or center line',
                'confidence': 0.8
            })

        return violations

    def _evaluate_visual_hierarchy(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate visual hierarchy."""
        violations = []

        # Check if hierarchy makes sense (larger elements higher in hierarchy)
        for i, elem_id in enumerate(analysis.visual_hierarchy):
            elem = next((e for e in analysis.elements if e.element_id == elem_id), None)
            if not elem:
                continue

            # Elements higher in hierarchy should generally be larger
            # This is a simplified check
            expected_size = 100 * (1 - i / len(analysis.visual_hierarchy))  # Decreasing size expectation
            actual_size = elem.bounding_box.area

            if actual_size > expected_size * 1.5 and i > 0:  # Too large for position
                violations.append({
                    'element_id': elem.element_id,
                    'message': f'Element {elem.element_id} too prominent for its hierarchy position',
                    'suggestion': 'Reduce size or adjust z-index to match visual importance',
                    'x': elem.bounding_box.x,
                    'y': elem.bounding_box.y,
                    'width': elem.bounding_box.width,
                    'height': elem.bounding_box.height,
                    'confidence': 0.6
                })

        return violations

    def _evaluate_brand_colors(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate brand color usage."""
        # This would need brand kit integration
        # Placeholder for now
        return []

    def _evaluate_brand_typography(self, analysis: LayoutAnalysis) -> List[Dict[str, Any]]:
        """Evaluate brand typography compliance."""
        # This would need brand kit integration
        # Placeholder for now
        return []