"""
Layout Optimization Web API.

Provides REST endpoints for layout analysis, optimization, and overlay generation.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ...layout_opt import (
    LayoutAnalyzer, LayoutOptimizer, LayoutVariants,
    OverlayGenerator, LayoutAnalysis, LayoutOverlay,
    OverlayType, VariantStrategy
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/layout-opt", tags=["layout-optimization"])


class LayoutDataModel(BaseModel):
    """Model for layout data input."""
    elements: List[Dict[str, Any]] = Field(..., description="Layout elements")
    canvas_width: float = Field(..., description="Canvas width")
    canvas_height: float = Field(..., description="Canvas height")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class OptimizationRequest(BaseModel):
    """Request model for layout optimization."""
    layout_data: LayoutDataModel
    optimization_level: str = Field("standard", description="Optimization level: basic, standard, advanced")
    generate_overlays: bool = Field(False, description="Generate visual overlays")
    overlay_types: Optional[List[str]] = Field(None, description="Specific overlay types to generate")


class VariantRequest(BaseModel):
    """Request model for layout variants."""
    layout_data: LayoutDataModel
    strategies: Optional[List[str]] = Field(None, description="Variant strategies to use")
    count_per_strategy: int = Field(3, description="Number of variants per strategy")


class AnalysisResponse(BaseModel):
    """Response model for layout analysis."""
    analysis: Dict[str, Any]
    score: Dict[str, Any]
    violations: List[Dict[str, Any]]
    recommendations: List[str]


class OptimizationResponse(BaseModel):
    """Response model for layout optimization."""
    optimized_layout: Dict[str, Any]
    actions_applied: List[Dict[str, Any]]
    improvement_score: float
    overlays: Optional[Dict[str, Any]] = None


class VariantResponse(BaseModel):
    """Response model for layout variants."""
    variants: List[Dict[str, Any]]
    strategies_used: List[str]
    total_generated: int


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_layout(layout_data: LayoutDataModel) -> AnalysisResponse:
    """
    Analyze a layout for design quality and issues.

    Args:
        layout_data: Layout data to analyze

    Returns:
        Analysis results with scores and recommendations
    """
    try:
        analyzer = LayoutAnalyzer()

        # Convert layout data to internal format
        layout_dict = layout_data.dict()

        # Perform analysis
        analysis = await analyzer.analyze_layout(layout_dict)

        # Get layout score
        from ...layout_opt import LayoutScorer
        scorer = LayoutScorer()
        score = await scorer.score_layout(analysis)

        # Get violations and recommendations
        violations = []
        recommendations = []

        for violation in score.violations:
            violations.append({
                'rule': violation.rule_name,
                'severity': violation.severity,
                'description': violation.description,
                'elements': violation.element_ids
            })
            recommendations.extend(violation.recommendations)

        return AnalysisResponse(
            analysis=analysis.to_dict(),
            score={
                'overall_score': score.overall_score,
                'dimensions': {dim.value: getattr(score, dim.value) for dim in score.dimensions.keys()},
                'weighted_score': score.weighted_score
            },
            violations=violations,
            recommendations=list(set(recommendations))  # Remove duplicates
        )

    except Exception as e:
        logger.error(f"Layout analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_layout(request: OptimizationRequest) -> OptimizationResponse:
    """
    Optimize a layout using AI-driven analysis.

    Args:
        request: Optimization request with layout data and options

    Returns:
        Optimized layout with applied actions
    """
    try:
        analyzer = LayoutAnalyzer()
        optimizer = LayoutOptimizer()

        # Convert layout data
        layout_dict = request.layout_data.dict()

        # Analyze layout
        analysis = await analyzer.analyze_layout(layout_dict)

        # Generate optimization actions
        actions = await optimizer.optimize_layout(
            analysis,
            level=request.optimization_level
        )

        # Apply actions
        optimized_layout = await optimizer.apply_actions(layout_dict, actions)

        # Calculate improvement score
        from ...layout_opt import LayoutScorer
        scorer = LayoutScorer()
        original_score = await scorer.score_layout(analysis)
        optimized_analysis = await analyzer.analyze_layout(optimized_layout)
        optimized_score = await scorer.score_layout(optimized_analysis)

        improvement = optimized_score.overall_score - original_score.overall_score

        # Generate overlays if requested
        overlays = None
        if request.generate_overlays:
            overlay_generator = OverlayGenerator()

            # Convert overlay types
            overlay_types = None
            if request.overlay_types:
                overlay_types = [OverlayType(t) for t in request.overlay_types]

            overlays = await overlay_generator.generate_overlays(
                optimized_analysis,
                actions,
                overlay_types
            )

        return OptimizationResponse(
            optimized_layout=optimized_layout,
            actions_applied=[action.to_dict() for action in actions],
            improvement_score=improvement,
            overlays=overlays.to_dict() if overlays else None
        )

    except Exception as e:
        logger.error(f"Layout optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/variants", response_model=VariantResponse)
async def generate_variants(request: VariantRequest) -> VariantResponse:
    """
    Generate multiple optimized variants of a layout.

    Args:
        request: Variant generation request

    Returns:
        Generated layout variants
    """
    try:
        variants_generator = LayoutVariants()

        # Convert layout data
        layout_dict = request.layout_data.dict()

        # Convert strategies
        strategies = None
        if request.strategies:
            strategies = [VariantStrategy(s) for s in request.strategies]

        # Generate variants
        variants = await variants_generator.generate_variants(
            layout_dict,
            strategies=strategies,
            count_per_strategy=request.count_per_strategy
        )

        return VariantResponse(
            variants=[v.to_dict() for v in variants],
            strategies_used=[s.value for s in variants_generator.strategies_used],
            total_generated=len(variants)
        )

    except Exception as e:
        logger.error(f"Variant generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Variant generation failed: {str(e)}")


@router.get("/overlay-types")
async def get_overlay_types() -> Dict[str, List[str]]:
    """
    Get available overlay types for visualization.

    Returns:
        List of available overlay types
    """
    return {
        "overlay_types": [t.value for t in OverlayType],
        "descriptions": {
            OverlayType.ALIGNMENT_GUIDES.value: "Show alignment guides for multiple elements",
            OverlayType.SPACING_INDICATORS.value: "Indicate spacing between elements",
            OverlayType.CONTRAST_WARNINGS.value: "Highlight potential contrast issues",
            OverlayType.SUGGESTED_MOVES.value: "Show suggested element repositioning",
            OverlayType.SIZE_SUGGESTIONS.value: "Indicate suggested size changes",
            OverlayType.RULE_OF_THIRDS.value: "Display rule of thirds grid",
            OverlayType.GOLDEN_RATIO.value: "Show golden ratio guides",
            OverlayType.VISUAL_HIERARCHY.value: "Indicate visual hierarchy levels"
        }
    }


@router.get("/strategies")
async def get_variant_strategies() -> Dict[str, List[str]]:
    """
    Get available variant generation strategies.

    Returns:
        List of available strategies
    """
    return {
        "strategies": [s.value for s in VariantStrategy],
        "descriptions": {
            VariantStrategy.CONSERVATIVE.value: "Minor improvements with low risk",
            VariantStrategy.BALANCED.value: "Balanced improvements and changes",
            VariantStrategy.AGGRESSIVE.value: "Major improvements with higher risk",
            VariantStrategy.CREATIVE.value: "Creative layout rearrangements",
            VariantStrategy.MINIMALIST.value: "Simplify and reduce elements",
            VariantStrategy.DYNAMIC.value: "Add movement and energy"
        }
    }


@router.post("/batch-optimize")
async def batch_optimize_layouts(layouts: List[LayoutDataModel],
                                background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Optimize multiple layouts in batch.

    Args:
        layouts: List of layout data to optimize
        background_tasks: FastAPI background tasks

    Returns:
        Task ID for tracking batch optimization
    """
    try:
        # This would typically be handled by the async engine
        # For now, return a placeholder response
        task_id = f"batch_opt_{len(layouts)}"

        # In a real implementation, this would submit to async engine
        background_tasks.add_task(_process_batch_optimization, layouts, task_id)

        return {
            "task_id": task_id,
            "layouts_count": len(layouts),
            "status": "processing"
        }

    except Exception as e:
        logger.error(f"Batch optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch optimization failed: {str(e)}")


async def _process_batch_optimization(layouts: List[LayoutDataModel], task_id: str):
    """Process batch layout optimization (placeholder)."""
    # Implementation would use async engine to process layouts
    logger.info(f"Processing batch optimization for {len(layouts)} layouts, task: {task_id}")
    # Actual implementation would be more complex