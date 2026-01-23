"""
Layout Scoring Engine for Comfy Gimpy Studio.

Scores layouts based on multiple quality dimensions using AI and heuristics.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

from .analyzer import LayoutAnalysis
from .heuristics import DesignHeuristics, RuleViolation, RuleSeverity

logger = logging.getLogger(__name__)


class ScoreDimension(Enum):
    """Dimensions used for layout scoring."""
    READABILITY = "readability"
    BALANCE = "balance"
    HIERARCHY = "hierarchy"
    CONTRAST = "contrast"
    HARMONY = "harmony"
    ALIGNMENT = "alignment"
    SPACING = "spacing"
    BRAND_COMPLIANCE = "brand_compliance"


@dataclass
class DimensionScore:
    """Score for a specific dimension."""
    dimension: ScoreDimension
    score: float  # 0.0 to 1.0
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Get the weighted score."""
        return self.score * self.weight


@dataclass
class LayoutScore:
    """Overall layout score with dimension breakdown."""
    overall_score: float = 0.0
    dimensions: Dict[ScoreDimension, DimensionScore] = field(default_factory=dict)
    violations: List[RuleViolation] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def score_breakdown(self) -> Dict[str, float]:
        """Get score breakdown by dimension."""
        return {
            dim.value: score.score
            for dim, score in self.dimensions.items()
        }

    @property
    def weighted_overall_score(self) -> float:
        """Calculate weighted overall score."""
        if not self.dimensions:
            return 0.0

        total_weight = sum(score.weight for score in self.dimensions.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(score.weighted_score for score in self.dimensions.values())
        return weighted_sum / total_weight


class LayoutScorer:
    """Scores layouts based on multiple quality dimensions."""

    def __init__(self):
        self.heuristics = DesignHeuristics()
        self.dimension_weights = self._get_default_weights()

    def _get_default_weights(self) -> Dict[ScoreDimension, float]:
        """Get default weights for scoring dimensions."""
        return {
            ScoreDimension.READABILITY: 1.0,
            ScoreDimension.BALANCE: 0.9,
            ScoreDimension.HIERARCHY: 0.8,
            ScoreDimension.CONTRAST: 0.9,
            ScoreDimension.HARMONY: 0.7,
            ScoreDimension.ALIGNMENT: 0.8,
            ScoreDimension.SPACING: 0.7,
            ScoreDimension.BRAND_COMPLIANCE: 0.6,
        }

    def set_dimension_weight(self, dimension: ScoreDimension, weight: float):
        """Set weight for a scoring dimension."""
        self.dimension_weights[dimension] = max(0.0, min(2.0, weight))  # Clamp to 0-2

    async def score_layout(self, analysis: LayoutAnalysis) -> LayoutScore:
        """
        Score a layout based on analysis results.

        Args:
            analysis: Layout analysis to score

        Returns:
            LayoutScore with overall score and dimension breakdown
        """
        logger.info("Starting layout scoring")

        score = LayoutScore()

        # Get rule violations
        score.violations = self.heuristics.evaluate_all(analysis)

        # Score each dimension
        score.dimensions = await self._score_all_dimensions(analysis, score.violations)

        # Calculate overall score
        score.overall_score = score.weighted_overall_score

        # Generate recommendations
        score.recommendations = self._generate_recommendations(score)

        logger.info(f"Layout scoring complete: {score.overall_score:.3f}")
        return score

    async def _score_all_dimensions(self, analysis: LayoutAnalysis,
                                  violations: List[RuleViolation]) -> Dict[ScoreDimension, DimensionScore]:
        """Score all dimensions."""
        dimensions = {}

        # Readability
        dimensions[ScoreDimension.READABILITY] = await self._score_readability(analysis, violations)

        # Balance
        dimensions[ScoreDimension.BALANCE] = await self._score_balance(analysis, violations)

        # Hierarchy
        dimensions[ScoreDimension.HIERARCHY] = await self._score_hierarchy(analysis, violations)

        # Contrast
        dimensions[ScoreDimension.CONTRAST] = await self._score_contrast(analysis, violations)

        # Harmony
        dimensions[ScoreDimension.HARMONY] = await self._score_harmony(analysis, violations)

        # Alignment
        dimensions[ScoreDimension.ALIGNMENT] = await self._score_alignment(analysis, violations)

        # Spacing
        dimensions[ScoreDimension.SPACING] = await self._score_spacing(analysis, violations)

        # Brand Compliance
        dimensions[ScoreDimension.BRAND_COMPLIANCE] = await self._score_brand_compliance(analysis, violations)

        # Apply weights
        for dim, score in dimensions.items():
            score.weight = self.dimension_weights.get(dim, 1.0)

        return dimensions

    async def _score_readability(self, analysis: LayoutAnalysis,
                               violations: List[RuleViolation]) -> DimensionScore:
        """Score text readability."""
        score = DimensionScore(dimension=ScoreDimension.READABILITY)

        # Start with analysis-based score
        base_score = analysis.text_readability_score

        # Penalize for readability violations
        readability_violations = [
            v for v in violations
            if v.category.value in ['typography'] and v.severity in [RuleSeverity.CRITICAL, RuleSeverity.HIGH]
        ]

        penalty = len(readability_violations) * 0.1  # 10% penalty per major violation
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(readability_violations),
            'penalty': penalty,
            'text_elements': len(analysis.text_elements)
        }

        return score

    async def _score_balance(self, analysis: LayoutAnalysis,
                           violations: List[RuleViolation]) -> DimensionScore:
        """Score visual balance."""
        score = DimensionScore(dimension=ScoreDimension.BALANCE)

        # Use analysis balance score as base
        base_score = analysis.visual_balance_score

        # Check for balance-related violations
        balance_violations = [
            v for v in violations
            if 'balance' in v.message.lower() or v.rule_id == 'visual_balance'
        ]

        penalty = len(balance_violations) * 0.15  # 15% penalty per balance issue
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(balance_violations),
            'penalty': penalty,
            'element_count': len(analysis.elements)
        }

        return score

    async def _score_hierarchy(self, analysis: LayoutAnalysis,
                             violations: List[RuleViolation]) -> DimensionScore:
        """Score visual hierarchy."""
        score = DimensionScore(dimension=ScoreDimension.HIERARCHY)

        # Analyze hierarchy from z-index and size
        elements = analysis.elements
        if not elements:
            score.score = 1.0  # Empty layout = perfect hierarchy
            return score

        # Check z-index distribution
        z_indices = [e.z_index for e in elements]
        unique_z = len(set(z_indices))

        # Check size distribution
        sizes = [e.bounding_box.area for e in elements]
        sizes.sort(reverse=True)

        # Calculate hierarchy score based on size ratios
        hierarchy_score = 0.0
        if len(sizes) > 1:
            # Check for clear size differences
            ratios = []
            for i in range(len(sizes) - 1):
                if sizes[i] > 0:
                    ratio = sizes[i + 1] / sizes[i]
                    ratios.append(ratio)

            # Good hierarchy has clear size differences (ratios < 0.7)
            good_ratios = sum(1 for r in ratios if r < 0.7)
            hierarchy_score = good_ratios / len(ratios) if ratios else 1.0

        # Penalize for hierarchy violations
        hierarchy_violations = [
            v for v in violations
            if v.category.value == 'hierarchy' or 'hierarchy' in v.message.lower()
        ]

        penalty = len(hierarchy_violations) * 0.1
        score.score = max(0.0, hierarchy_score - penalty)

        score.details = {
            'hierarchy_score': hierarchy_score,
            'z_index_levels': unique_z,
            'size_ratios': ratios[:5],  # First 5 ratios
            'violations_count': len(hierarchy_violations),
            'penalty': penalty
        }

        return score

    async def _score_contrast(self, analysis: LayoutAnalysis,
                            violations: List[RuleViolation]) -> DimensionScore:
        """Score color and text contrast."""
        score = DimensionScore(dimension=ScoreDimension.CONTRAST)

        # Use analysis contrast score as base
        base_score = analysis.color_contrast_score

        # Check for contrast violations
        contrast_violations = [
            v for v in violations
            if 'contrast' in v.message.lower() or v.rule_id in ['text_contrast', 'color_contrast']
        ]

        penalty = len(contrast_violations) * 0.2  # 20% penalty per contrast issue
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(contrast_violations),
            'penalty': penalty,
            'color_count': len(analysis.dominant_colors)
        }

        return score

    async def _score_harmony(self, analysis: LayoutAnalysis,
                           violations: List[RuleViolation]) -> DimensionScore:
        """Score color harmony."""
        score = DimensionScore(dimension=ScoreDimension.HARMONY)

        # Analyze color relationships
        colors = analysis.dominant_colors
        harmony_score = 0.5  # Default neutral score

        if len(colors) == 1:
            harmony_score = 0.8  # Single color is harmonious
        elif len(colors) == 2:
            harmony_score = 0.7  # Two colors can work well
        elif 3 <= len(colors) <= 5:
            harmony_score = 0.9  # Good range for harmony
        elif len(colors) > 5:
            harmony_score = 0.4  # Too many colors reduce harmony
        else:
            harmony_score = 0.3  # Very few colors may be boring

        # Check for harmony violations
        harmony_violations = [
            v for v in violations
            if 'harmony' in v.message.lower() or v.rule_id == 'color_harmony'
        ]

        penalty = len(harmony_violations) * 0.15
        score.score = max(0.0, harmony_score - penalty)

        score.details = {
            'harmony_score': harmony_score,
            'color_count': len(colors),
            'violations_count': len(harmony_violations),
            'penalty': penalty
        }

        return score

    async def _score_alignment(self, analysis: LayoutAnalysis,
                             violations: List[RuleViolation]) -> DimensionScore:
        """Score element alignment."""
        score = DimensionScore(dimension=ScoreDimension.ALIGNMENT)

        # Use analysis alignment score as base
        base_score = analysis.alignment_score

        # Check for alignment violations
        alignment_violations = [
            v for v in violations
            if v.category.value == 'alignment' or 'alignment' in v.message.lower()
        ]

        penalty = len(alignment_violations) * 0.1
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(alignment_violations),
            'penalty': penalty
        }

        return score

    async def _score_spacing(self, analysis: LayoutAnalysis,
                           violations: List[RuleViolation]) -> DimensionScore:
        """Score spacing consistency."""
        score = DimensionScore(dimension=ScoreDimension.SPACING)

        # Use analysis spacing score as base
        base_score = analysis.spacing_consistency_score

        # Check for spacing violations
        spacing_violations = [
            v for v in violations
            if v.category.value == 'spacing' or 'spacing' in v.message.lower()
        ]

        penalty = len(spacing_violations) * 0.1
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(spacing_violations),
            'penalty': penalty,
            'avg_horizontal_spacing': analysis.spacing.average_horizontal,
            'avg_vertical_spacing': analysis.spacing.average_vertical
        }

        return score

    async def _score_brand_compliance(self, analysis: LayoutAnalysis,
                                    violations: List[RuleViolation]) -> DimensionScore:
        """Score brand compliance."""
        score = DimensionScore(dimension=ScoreDimension.BRAND_COMPLIANCE)

        # Check for brand-related violations
        brand_violations = [
            v for v in violations
            if v.category.value == 'brand'
        ]

        # Base score assumes compliance unless violations found
        base_score = 0.8  # Assume mostly compliant
        penalty = len(brand_violations) * 0.25  # 25% penalty per brand violation
        score.score = max(0.0, base_score - penalty)

        score.details = {
            'base_score': base_score,
            'violations_count': len(brand_violations),
            'penalty': penalty,
            'brand_colors_used': len([c for c in analysis.color_usage if c.is_brand_color])
        }

        return score

    def _generate_recommendations(self, layout_score: LayoutScore) -> List[str]:
        """Generate recommendations based on scoring results."""
        recommendations = []

        # Sort violations by severity
        critical_violations = [v for v in layout_score.violations if v.severity == RuleSeverity.CRITICAL]
        high_violations = [v for v in layout_score.violations if v.severity == RuleSeverity.HIGH]

        # Add critical recommendations first
        for violation in critical_violations[:3]:  # Top 3 critical issues
            recommendations.append(f"CRITICAL: {violation.suggestion}")

        # Add high priority recommendations
        for violation in high_violations[:3]:  # Top 3 high priority issues
            recommendations.append(f"HIGH: {violation.suggestion}")

        # Add dimension-based recommendations
        for dim, score in layout_score.dimensions.items():
            if score.score < 0.6:  # Below 60% is concerning
                recommendations.append(f"Improve {dim.value}: {self._get_dimension_recommendation(dim)}")

        # Add general recommendations if score is low
        if layout_score.overall_score < 0.5:
            recommendations.append("Consider using layout optimization to automatically improve the design")
        elif layout_score.overall_score < 0.7:
            recommendations.append("Review the suggestions panel for specific improvements")

        return recommendations[:10]  # Limit to top 10 recommendations

    def _get_dimension_recommendation(self, dimension: ScoreDimension) -> str:
        """Get recommendation text for a dimension."""
        recommendations = {
            ScoreDimension.READABILITY: "Increase font sizes, improve text contrast, or shorten line lengths",
            ScoreDimension.BALANCE: "Adjust element positions or sizes for better visual balance",
            ScoreDimension.HIERARCHY: "Create clearer size relationships between elements",
            ScoreDimension.CONTRAST: "Use colors with better contrast ratios",
            ScoreDimension.HARMONY: "Simplify color palette or use complementary colors",
            ScoreDimension.ALIGNMENT: "Align elements to common edges or center lines",
            ScoreDimension.SPACING: "Standardize spacing between elements",
            ScoreDimension.BRAND_COMPLIANCE: "Apply brand kit colors and typography"
        }
        return recommendations.get(dimension, f"Review {dimension.value} guidelines")

    def get_scoring_weights(self) -> Dict[str, float]:
        """Get current scoring weights."""
        return {dim.value: weight for dim, weight in self.dimension_weights.items()}

    def update_scoring_weights(self, weights: Dict[str, float]):
        """Update scoring weights."""
        for dim_name, weight in weights.items():
            try:
                dimension = ScoreDimension(dim_name)
                self.set_dimension_weight(dimension, weight)
            except ValueError:
                logger.warning(f"Unknown scoring dimension: {dim_name}")