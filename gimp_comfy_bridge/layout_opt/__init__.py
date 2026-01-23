"""
AI-Driven Layout Optimization for Comfy Gimpy Studio.

This module provides intelligent layout analysis, optimization, and improvement
capabilities for templates and designs using AI, heuristics, and design rules.
"""

from .analyzer import LayoutAnalyzer, LayoutAnalysis, LayoutElement, BoundingBox
from .heuristics import DesignHeuristics, DesignRule, RuleCategory, RuleViolation
from .scorer import LayoutScorer, LayoutScore, ScoreDimension, ViolationAnalysis
from .optimizer import LayoutOptimizer, OptimizationAction, OptimizationActionType
from .variants import VariantGenerator, LayoutVariant, VariantStrategy
from .overlays import OverlayGenerator, LayoutOverlay, OverlayType, OverlayElement

__all__ = [
    # Analysis
    'LayoutAnalyzer',
    'LayoutAnalysis',
    'LayoutElement',
    'BoundingBox',

    # Heuristics
    'DesignHeuristics',
    'DesignRule',
    'RuleCategory',
    'RuleViolation',

    # Scoring
    'LayoutScorer',
    'LayoutScore',
    'ScoreDimension',
    'ViolationAnalysis',

    # Optimization
    'LayoutOptimizer',
    'OptimizationAction',
    'OptimizationActionType',

    # Variants
    'VariantGenerator',
    'LayoutVariant',
    'VariantStrategy',

    # Overlays
    'OverlayGenerator',
    'LayoutOverlay',
    'OverlayType',
    'OverlayElement',
]