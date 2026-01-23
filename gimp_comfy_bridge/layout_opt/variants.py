"""
Layout Variants Generator for Comfy Gimpy Studio.

Generates multiple optimized variants of layouts with different strategies.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import copy
import random
import asyncio

from .analyzer import LayoutAnalysis
from .scorer import LayoutScorer, LayoutScore
from .optimizer import LayoutOptimizer, OptimizationResult, OptimizationAction

logger = logging.getLogger(__name__)


class VariantStrategy(Enum):
    """Strategies for generating layout variants."""
    CONSERVATIVE = "conservative"  # Small, safe changes
    BALANCED = "balanced"         # Moderate improvements
    AGGRESSIVE = "aggressive"     # Major restructuring
    CREATIVE = "creative"         # Experimental approaches
    MINIMALIST = "minimalist"     # Simplify and clean
    DYNAMIC = "dynamic"          # Add movement/energy


@dataclass
class LayoutVariant:
    """Represents a generated layout variant."""
    variant_id: str
    name: str
    description: str
    strategy: VariantStrategy
    score: float
    improvement: float
    actions_applied: List[OptimizationAction]
    analysis: LayoutAnalysis
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_improved(self) -> bool:
        """Check if this variant is an improvement."""
        return self.improvement > 0.01  # At least 1% improvement


@dataclass
class VariantGenerationResult:
    """Result of variant generation."""
    original_score: float
    variants: List[LayoutVariant]
    best_variant: Optional[LayoutVariant]
    generation_time: float

    @property
    def improved_variants(self) -> List[LayoutVariant]:
        """Get variants that are improvements."""
        return [v for v in self.variants if v.is_improved]

    @property
    def average_improvement(self) -> float:
        """Get average improvement across all variants."""
        if not self.variants:
            return 0.0
        return sum(v.improvement for v in self.variants) / len(self.variants)


class VariantGenerator:
    """Generates multiple optimized layout variants."""

    def __init__(self):
        self.scorer = LayoutScorer()
        self.optimizer = LayoutOptimizer()
        self.max_variants = 5
        self.generation_timeout = 30.0  # seconds

    async def generate_optimized_variants(self, template_data: Dict[str, Any],
                                        count: int = 3) -> VariantGenerationResult:
        """
        Generate multiple optimized variants of a layout.

        Args:
            template_data: Template data to generate variants for
            count: Number of variants to generate

        Returns:
            VariantGenerationResult with generated variants
        """
        import time
        start_time = time.time()

        logger.info(f"Generating {count} layout variants")

        # Analyze original layout
        from .analyzer import LayoutAnalyzer
        analyzer = LayoutAnalyzer()
        original_analysis = await analyzer.analyze_layout(template_data)
        original_score = await self.scorer.score_layout(original_analysis)

        # Generate variants
        variants = []
        strategies = list(VariantStrategy)

        for i in range(min(count, len(strategies))):
            try:
                strategy = strategies[i]
                variant = await self._generate_variant(
                    original_analysis,
                    original_score,
                    strategy,
                    i + 1
                )
                if variant:
                    variants.append(variant)
            except Exception as e:
                logger.warning(f"Failed to generate variant {i+1}: {e}")

        # Sort variants by score improvement
        variants.sort(key=lambda v: v.improvement, reverse=True)

        # Find best variant
        best_variant = variants[0] if variants else None

        generation_time = time.time() - start_time

        result = VariantGenerationResult(
            original_score=original_score.overall_score,
            variants=variants,
            best_variant=best_variant,
            generation_time=generation_time
        )

        logger.info(f"Generated {len(variants)} variants in {generation_time:.2f}s")
        return result

    async def _generate_variant(self, original_analysis: LayoutAnalysis,
                              original_score: LayoutScore,
                              strategy: VariantStrategy,
                              variant_num: int) -> Optional[LayoutVariant]:
        """Generate a single variant using specified strategy."""
        variant_id = f"variant_{variant_num}_{strategy.value}"

        # Create variant name and description
        name, description = self._get_variant_info(strategy)

        # Generate actions based on strategy
        actions = await self._generate_strategy_actions(
            original_analysis,
            original_score,
            strategy
        )

        if not actions:
            logger.debug(f"No actions generated for strategy {strategy.value}")
            return None

        # Apply actions to create new analysis
        variant_analysis = await self._apply_actions_to_analysis(
            original_analysis,
            actions
        )

        # Score the variant
        variant_score = await self.scorer.score_layout(variant_analysis)
        improvement = variant_score.overall_score - original_score.overall_score

        # Create variant
        variant = LayoutVariant(
            variant_id=variant_id,
            name=name,
            description=description,
            strategy=strategy,
            score=variant_score.overall_score,
            improvement=improvement,
            actions_applied=actions,
            analysis=variant_analysis,
            metadata={
                'strategy': strategy.value,
                'actions_count': len(actions),
                'generation_method': 'ai_optimized'
            }
        )

        return variant

    def _get_variant_info(self, strategy: VariantStrategy) -> Tuple[str, str]:
        """Get name and description for a strategy."""
        info = {
            VariantStrategy.CONSERVATIVE: ("Conservative Optimization", "Small, safe improvements to layout quality"),
            VariantStrategy.BALANCED: ("Balanced Optimization", "Moderate improvements balancing all aspects"),
            VariantStrategy.AGGRESSIVE: ("Aggressive Optimization", "Major restructuring for maximum improvement"),
            VariantStrategy.CREATIVE: ("Creative Layout", "Experimental approach with creative elements"),
            VariantStrategy.MINIMALIST: ("Minimalist Design", "Simplified, clean layout focusing on essentials"),
            VariantStrategy.DYNAMIC: ("Dynamic Layout", "Energetic design with movement and flow")
        }
        return info.get(strategy, ("Custom Variant", "Custom layout optimization"))

    async def _generate_strategy_actions(self, analysis: LayoutAnalysis,
                                       score: LayoutScore,
                                       strategy: VariantStrategy) -> List[OptimizationAction]:
        """Generate actions based on strategy."""
        if strategy == VariantStrategy.CONSERVATIVE:
            return await self._generate_conservative_actions(analysis, score)
        elif strategy == VariantStrategy.BALANCED:
            return await self._generate_balanced_actions(analysis, score)
        elif strategy == VariantStrategy.AGGRESSIVE:
            return await self._generate_aggressive_actions(analysis, score)
        elif strategy == VariantStrategy.CREATIVE:
            return await self._generate_creative_actions(analysis, score)
        elif strategy == VariantStrategy.MINIMALIST:
            return await self._generate_minimalist_actions(analysis, score)
        elif strategy == VariantStrategy.DYNAMIC:
            return await self._generate_dynamic_actions(analysis, score)
        else:
            return await self.optimizer._generate_actions(analysis, score)

    async def _generate_conservative_actions(self, analysis: LayoutAnalysis,
                                           score: LayoutScore) -> List[OptimizationAction]:
        """Generate conservative, low-risk actions."""
        actions = []

        # Focus on high-confidence, low-impact improvements
        if score.violations:
            # Only fix critical violations
            critical_violations = [v for v in score.violations if v.severity.value == 'critical']
            for violation in critical_violations[:2]:  # Max 2 actions
                action = await self.optimizer._create_action_from_violation(violation, analysis)
                if action and action.confidence > 0.7:
                    actions.append(action)

        # Small readability improvements
        readability_actions = await self.optimizer._generate_readability_actions(analysis)
        actions.extend(readability_actions[:1])  # Max 1 readability action

        return actions[:3]  # Limit to 3 total actions

    async def _generate_balanced_actions(self, analysis: LayoutAnalysis,
                                       score: LayoutScore) -> List[OptimizationAction]:
        """Generate balanced actions across all dimensions."""
        actions = []

        # Address each low-scoring dimension
        for dim, dim_score in score.dimensions.items():
            if dim_score.score < 0.7:  # Below 70%
                dim_actions = await self.optimizer._generate_dimension_specific_actions(
                    dim, analysis, dim_score
                )
                actions.extend(dim_actions[:1])  # 1 action per dimension

        # Add some general improvements
        general_actions = await self.optimizer._generate_general_actions(analysis)
        actions.extend(general_actions[:2])

        return actions[:5]  # Limit to 5 actions

    async def _generate_aggressive_actions(self, analysis: LayoutAnalysis,
                                         score: LayoutScore) -> List[OptimizationAction]:
        """Generate aggressive actions for maximum improvement."""
        actions = []

        # Fix all violations
        for violation in score.violations[:5]:  # Top 5 violations
            action = await self.optimizer._create_action_from_violation(violation, analysis)
            if action:
                actions.append(action)

        # Major restructuring actions
        if len(analysis.elements) > 3:
            # Reorder hierarchy
            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.REORDER_HIERARCHY,
                element_id=None,
                description="Restructure element hierarchy for better flow",
                confidence=0.6,
                params={'new_order': self._generate_optimal_hierarchy(analysis)},
                expected_improvement=0.1
            ))

        # Major spacing overhaul
        actions.append(OptimizationAction(
            action_type=self.optimizer.OptimizationActionType.ADJUST_SPACING,
            element_id=None,
            description="Complete spacing optimization",
            confidence=0.5,
            params={'comprehensive': True},
            expected_improvement=0.08
        ))

        return actions

    async def _generate_creative_actions(self, analysis: LayoutAnalysis,
                                       score: LayoutScore) -> List[OptimizationAction]:
        """Generate creative, experimental actions."""
        actions = []

        # Add some randomness to positioning
        for element in analysis.elements[:2]:  # First 2 elements
            # Random but guided movement
            canvas_center_x = analysis.canvas_width / 2
            elem_center_x = element.bounding_box.center[0]

            # Move toward rule of thirds with some randomness
            third_width = analysis.canvas_width / 3
            targets = [third_width, 2 * third_width]
            target_x = random.choice(targets)

            move_distance = (target_x - elem_center_x) * 0.7 + random.uniform(-20, 20)
            new_x = element.bounding_box.x + move_distance

            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.MOVE_ELEMENT,
                element_id=element.element_id,
                description="Creative repositioning for visual interest",
                confidence=0.4,
                params={'x': new_x, 'y': element.bounding_box.y},
                expected_improvement=0.02
            ))

        # Experiment with sizes
        large_elements = [e for e in analysis.elements if e.bounding_box.area > analysis.canvas_width * analysis.canvas_height * 0.1]
        if large_elements:
            element = random.choice(large_elements)
            scale_factor = random.uniform(0.8, 1.2)
            new_width = element.bounding_box.width * scale_factor
            new_height = element.bounding_box.height * scale_factor

            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.RESIZE_ELEMENT,
                element_id=element.element_id,
                description="Experimental size adjustment",
                confidence=0.3,
                params={'width': new_width, 'height': new_height},
                expected_improvement=0.01
            ))

        return actions

    async def _generate_minimalist_actions(self, analysis: LayoutAnalysis,
                                         score: LayoutScore) -> List[OptimizationAction]:
        """Generate minimalist simplification actions."""
        actions = []

        # Increase spacing for breathing room
        actions.append(OptimizationAction(
            action_type=self.optimizer.OptimizationActionType.ADJUST_SPACING,
            element_id=None,
            description="Increase spacing for minimalist aesthetic",
            confidence=0.7,
            params={'multiplier': 1.5, 'minimalist': True},
            expected_improvement=0.05
        ))

        # Simplify color palette
        if len(analysis.dominant_colors) > 3:
            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.CHANGE_COLOR,
                element_id=None,
                description="Reduce color palette for minimalist design",
                confidence=0.6,
                params={'simplify_colors': True, 'target_colors': 2},
                expected_improvement=0.03
            ))

        # Clean alignment
        actions.append(OptimizationAction(
            action_type=self.optimizer.OptimizationActionType.ALIGN_ELEMENTS,
            element_id=None,
            description="Clean, minimal alignment",
            confidence=0.8,
            params={'alignment': 'grid', 'spacing': 'generous'},
            expected_improvement=0.04
        ))

        return actions

    async def _generate_dynamic_actions(self, analysis: LayoutAnalysis,
                                      score: LayoutScore) -> List[OptimizationAction]:
        """Generate dynamic, energetic actions."""
        actions = []

        # Create diagonal flow
        elements = sorted(analysis.elements, key=lambda e: e.bounding_box.x)
        for i, element in enumerate(elements):
            # Create diagonal movement
            diagonal_offset = (i / len(elements)) * 50
            new_y = element.bounding_box.y + diagonal_offset * (-1 if i % 2 == 0 else 1)

            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.MOVE_ELEMENT,
                element_id=element.element_id,
                description="Create dynamic diagonal flow",
                confidence=0.5,
                params={'x': element.bounding_box.x, 'y': new_y},
                expected_improvement=0.02
            ))

        # Add size variation for energy
        for element in analysis.elements[::2]:  # Every other element
            scale_factor = random.uniform(1.1, 1.3)
            new_width = element.bounding_box.width * scale_factor
            new_height = element.bounding_box.height * scale_factor

            actions.append(OptimizationAction(
                action_type=self.optimizer.OptimizationActionType.RESIZE_ELEMENT,
                element_id=element.element_id,
                description="Add size variation for dynamic energy",
                confidence=0.4,
                params={'width': new_width, 'height': new_height},
                expected_improvement=0.01
            ))

        return actions

    def _generate_optimal_hierarchy(self, analysis: LayoutAnalysis) -> List[str]:
        """Generate optimal element hierarchy order."""
        # Sort by size (largest first) then by position
        elements = sorted(
            analysis.elements,
            key=lambda e: (e.bounding_box.area, -e.bounding_box.y, e.bounding_box.x),
            reverse=True
        )
        return [e.element_id for e in elements]

    async def _apply_actions_to_analysis(self, analysis: LayoutAnalysis,
                                       actions: List[OptimizationAction]) -> LayoutAnalysis:
        """Apply actions to create new analysis."""
        return await self.optimizer._apply_actions(analysis, actions)

    def set_max_variants(self, max_variants: int):
        """Set maximum number of variants to generate."""
        self.max_variants = max(1, max_variants)

    def set_generation_timeout(self, timeout: float):
        """Set generation timeout in seconds."""
        self.generation_timeout = max(1.0, timeout)