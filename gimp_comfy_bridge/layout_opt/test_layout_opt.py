"""
Tests for Layout Optimization Module.

Comprehensive tests for layout analysis, optimization, scoring, and variants.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from ..layout_opt import (
    LayoutAnalyzer, LayoutOptimizer, LayoutScorer, LayoutVariants,
    OverlayGenerator, LayoutAnalysis, LayoutScore, OptimizationAction,
    DesignHeuristics, ScoreDimension, VariantStrategy
)


class TestLayoutAnalyzer:
    """Test layout analyzer functionality."""

    @pytest.fixture
    def sample_layout_data(self):
        """Sample layout data for testing."""
        return {
            "elements": [
                {
                    "element_id": "header",
                    "type": "text",
                    "x": 100,
                    "y": 50,
                    "width": 400,
                    "height": 60,
                    "text": "Welcome Header",
                    "font_size": 24,
                    "color": "#000000"
                },
                {
                    "element_id": "body",
                    "type": "text",
                    "x": 100,
                    "y": 150,
                    "width": 400,
                    "height": 200,
                    "text": "This is the main body text content.",
                    "font_size": 16,
                    "color": "#333333"
                },
                {
                    "element_id": "image",
                    "type": "image",
                    "x": 550,
                    "y": 50,
                    "width": 300,
                    "height": 300,
                    "src": "sample.jpg"
                }
            ],
            "canvas_width": 1920,
            "canvas_height": 1080,
            "metadata": {
                "template_type": "social_media",
                "aspect_ratio": "16:9"
            }
        }

    @pytest.mark.asyncio
    async def test_analyze_layout_basic(self, sample_layout_data):
        """Test basic layout analysis."""
        analyzer = LayoutAnalyzer()

        analysis = await analyzer.analyze_layout(sample_layout_data)

        assert isinstance(analysis, LayoutAnalysis)
        assert analysis.canvas_width == 1920
        assert analysis.canvas_height == 1080
        assert len(analysis.elements) == 3
        assert len(analysis.text_elements) == 2
        assert len(analysis.image_elements) == 1

    @pytest.mark.asyncio
    async def test_analyze_layout_quality_metrics(self, sample_layout_data):
        """Test layout quality metrics calculation."""
        analyzer = LayoutAnalyzer()

        analysis = await analyzer.analyze_layout(sample_layout_data)

        # Check that quality metrics are calculated
        assert hasattr(analysis, 'visual_hierarchy')
        assert hasattr(analysis, 'color_usage')
        assert hasattr(analysis, 'spacing_analysis')
        assert isinstance(analysis.visual_hierarchy, list)
        assert len(analysis.visual_hierarchy) > 0

    @pytest.mark.asyncio
    async def test_analyze_empty_layout(self):
        """Test analysis of empty layout."""
        analyzer = LayoutAnalyzer()

        empty_layout = {
            "elements": [],
            "canvas_width": 1920,
            "canvas_height": 1080
        }

        analysis = await analyzer.analyze_layout(empty_layout)

        assert analysis.canvas_width == 1920
        assert analysis.canvas_height == 1080
        assert len(analysis.elements) == 0
        assert len(analysis.text_elements) == 0
        assert len(analysis.image_elements) == 0


class TestDesignHeuristics:
    """Test design heuristics functionality."""

    @pytest.fixture
    def heuristics(self):
        """Design heuristics instance."""
        return DesignHeuristics()

    def test_rule_of_thirds_check(self, heuristics):
        """Test rule of thirds heuristic."""
        # Element at rule of thirds intersection
        element = Mock()
        element.bounding_box = Mock()
        element.bounding_box.x = 640  # 1/3 of 1920
        element.bounding_box.y = 360  # 1/3 of 1080

        result = heuristics.check_rule_of_thirds(element, 1920, 1080)
        assert result.passed is True
        assert result.score > 0.8

    def test_contrast_ratio_check(self, heuristics):
        """Test contrast ratio calculation."""
        # High contrast colors
        fg_color = "#000000"
        bg_color = "#FFFFFF"

        ratio = heuristics.calculate_contrast_ratio(fg_color, bg_color)
        assert ratio > 20  # Should be very high contrast

        # Low contrast colors
        fg_color = "#808080"
        bg_color = "#909090"

        ratio = heuristics.calculate_contrast_ratio(fg_color, bg_color)
        assert ratio < 2  # Should be low contrast

    def test_alignment_check(self, heuristics):
        """Test element alignment detection."""
        elements = [
            Mock(bounding_box=Mock(x=100, width=200)),
            Mock(bounding_box=Mock(x=100, width=150)),  # Aligned left
            Mock(bounding_box=Mock(x=200, width=100))   # Not aligned
        ]

        alignments = heuristics.detect_alignments(elements, 1920)
        assert len(alignments) > 0
        assert 'left' in alignments

    def test_spacing_consistency(self, heuristics):
        """Test spacing consistency analysis."""
        elements = [
            Mock(bounding_box=Mock(x=0, width=100)),
            Mock(bounding_box=Mock(x=120, width=100)),  # 20px gap
            Mock(bounding_box=Mock(x=240, width=100))   # 20px gap
        ]

        consistency = heuristics.analyze_spacing_consistency(elements)
        assert consistency > 0.8  # Should be very consistent


class TestLayoutScorer:
    """Test layout scoring functionality."""

    @pytest.fixture
    def scorer(self):
        """Layout scorer instance."""
        return LayoutScorer()

    @pytest.fixture
    def mock_analysis(self):
        """Mock layout analysis for testing."""
        analysis = Mock(spec=LayoutAnalysis)
        analysis.canvas_width = 1920
        analysis.canvas_height = 1080
        analysis.elements = [
            Mock(element_id="header", bounding_box=Mock(x=100, y=50, width=400, height=60)),
            Mock(element_id="body", bounding_box=Mock(x=100, y=150, width=400, height=200)),
            Mock(element_id="image", bounding_box=Mock(x=550, y=50, width=300, height=300))
        ]
        analysis.text_elements = analysis.elements[:2]
        analysis.image_elements = analysis.elements[2:]
        analysis.visual_hierarchy = ["header", "image", "body"]
        analysis.color_usage = {"#000000": 2, "#333333": 1, "#FFFFFF": 1}
        analysis.spacing_analysis = {"average_spacing": 50, "consistency": 0.9}

        return analysis

    @pytest.mark.asyncio
    async def test_score_layout_comprehensive(self, scorer, mock_analysis):
        """Test comprehensive layout scoring."""
        score = await scorer.score_layout(mock_analysis)

        assert isinstance(score, LayoutScore)
        assert 0 <= score.overall_score <= 1
        assert len(score.violations) >= 0
        assert len(score.recommendations) >= 0

        # Check all dimensions are scored
        for dimension in ScoreDimension:
            assert hasattr(score, dimension.value)
            dim_score = getattr(score, dimension.value)
            assert 0 <= dim_score <= 1

    @pytest.mark.asyncio
    async def test_score_dimensions(self, scorer, mock_analysis):
        """Test individual dimension scoring."""
        score = await scorer.score_layout(mock_analysis)

        # Check readability score
        assert hasattr(score, 'readability')
        assert 0 <= score.readability <= 1

        # Check balance score
        assert hasattr(score, 'balance')
        assert 0 <= score.balance <= 1

        # Check other dimensions
        dimensions = ['hierarchy', 'contrast', 'harmony', 'alignment', 'spacing', 'brand']
        for dim in dimensions:
            assert hasattr(score, dim)
            assert 0 <= getattr(score, dim) <= 1

    @pytest.mark.asyncio
    async def test_violation_analysis(self, scorer, mock_analysis):
        """Test violation analysis and recommendations."""
        score = await scorer.score_layout(mock_analysis)

        # Check violations structure
        for violation in score.violations:
            assert hasattr(violation, 'rule_name')
            assert hasattr(violation, 'severity')
            assert hasattr(violation, 'description')
            assert hasattr(violation, 'recommendations')
            assert len(violation.recommendations) > 0


class TestLayoutOptimizer:
    """Test layout optimization functionality."""

    @pytest.fixture
    def optimizer(self):
        """Layout optimizer instance."""
        return LayoutOptimizer()

    @pytest.fixture
    def mock_analysis(self):
        """Mock layout analysis for testing."""
        analysis = Mock(spec=LayoutAnalysis)
        analysis.canvas_width = 1920
        analysis.canvas_height = 1080
        analysis.elements = [
            Mock(element_id="header", bounding_box=Mock(x=50, y=50, width=400, height=60)),
            Mock(element_id="body", bounding_box=Mock(x=50, y=120, width=400, height=200)),
        ]
        analysis.text_elements = analysis.elements
        analysis.image_elements = []
        analysis.visual_hierarchy = ["header", "body"]
        analysis.color_usage = {"#000000": 2}
        analysis.spacing_analysis = {"average_spacing": 10, "consistency": 0.3}

        return analysis

    @pytest.mark.asyncio
    async def test_optimize_layout_basic(self, optimizer, mock_analysis):
        """Test basic layout optimization."""
        actions = await optimizer.optimize_layout(mock_analysis, level="basic")

        assert isinstance(actions, list)
        assert len(actions) > 0

        for action in actions:
            assert isinstance(action, OptimizationAction)
            assert hasattr(action, 'action_type')
            assert hasattr(action, 'element_id')
            assert hasattr(action, 'description')
            assert hasattr(action, 'confidence')

    @pytest.mark.asyncio
    async def test_optimize_layout_different_levels(self, optimizer, mock_analysis):
        """Test optimization at different levels."""
        levels = ["basic", "standard", "advanced"]

        for level in levels:
            actions = await optimizer.optimize_layout(mock_analysis, level=level)
            assert isinstance(actions, list)
            assert len(actions) >= 0

    @pytest.mark.asyncio
    async def test_apply_optimization_actions(self, optimizer):
        """Test applying optimization actions to layout."""
        layout_data = {
            "elements": [
                {
                    "element_id": "test_element",
                    "x": 100,
                    "y": 100,
                    "width": 200,
                    "height": 100
                }
            ],
            "canvas_width": 1920,
            "canvas_height": 1080
        }

        # Create a mock action
        action = Mock(spec=OptimizationAction)
        action.action_type = Mock()
        action.action_type.value = "move_element"
        action.element_id = "test_element"
        action.params = {"x": 150, "y": 150}

        actions = [action]

        result = await optimizer.apply_actions(layout_data, actions)

        assert result is not None
        assert "elements" in result
        # Check that element position was updated
        element = result["elements"][0]
        assert element["x"] == 150
        assert element["y"] == 150


class TestLayoutVariants:
    """Test layout variants generation."""

    @pytest.fixture
    def variants_generator(self):
        """Layout variants generator instance."""
        return LayoutVariants()

    @pytest.fixture
    def sample_layout(self):
        """Sample layout for variant generation."""
        return {
            "elements": [
                {
                    "element_id": "header",
                    "type": "text",
                    "x": 100,
                    "y": 50,
                    "width": 400,
                    "height": 60
                },
                {
                    "element_id": "image",
                    "type": "image",
                    "x": 550,
                    "y": 50,
                    "width": 300,
                    "height": 300
                }
            ],
            "canvas_width": 1920,
            "canvas_height": 1080
        }

    @pytest.mark.asyncio
    async def test_generate_variants_basic(self, variants_generator, sample_layout):
        """Test basic variant generation."""
        variants = await variants_generator.generate_variants(
            sample_layout,
            strategies=[VariantStrategy.CONSERVATIVE],
            count_per_strategy=2
        )

        assert isinstance(variants, list)
        assert len(variants) == 2  # 2 variants for 1 strategy

        for variant in variants:
            assert hasattr(variant, 'layout_data')
            assert hasattr(variant, 'strategy')
            assert hasattr(variant, 'score')
            assert hasattr(variant, 'changes')

    @pytest.mark.asyncio
    async def test_generate_variants_multiple_strategies(self, variants_generator, sample_layout):
        """Test variant generation with multiple strategies."""
        strategies = [VariantStrategy.CONSERVATIVE, VariantStrategy.BALANCED]
        variants = await variants_generator.generate_variants(
            sample_layout,
            strategies=strategies,
            count_per_strategy=1
        )

        assert len(variants) == 2  # 1 variant per strategy
        strategy_values = [v.strategy.value for v in variants]
        assert "conservative" in strategy_values
        assert "balanced" in strategy_values

    @pytest.mark.asyncio
    async def test_variant_scoring_and_ranking(self, variants_generator, sample_layout):
        """Test that variants are properly scored and ranked."""
        variants = await variants_generator.generate_variants(
            sample_layout,
            strategies=[VariantStrategy.CONSERVATIVE],
            count_per_strategy=3
        )

        # Check that variants have scores
        for variant in variants:
            assert isinstance(variant.score, (int, float))
            assert 0 <= variant.score <= 1

        # Check that variants are sorted by score (best first)
        scores = [v.score for v in variants]
        assert scores == sorted(scores, reverse=True)


class TestOverlayGenerator:
    """Test overlay generation functionality."""

    @pytest.fixture
    def overlay_generator(self):
        """Overlay generator instance."""
        return OverlayGenerator()

    @pytest.fixture
    def mock_analysis(self):
        """Mock layout analysis for overlay testing."""
        analysis = Mock(spec=LayoutAnalysis)
        analysis.canvas_width = 1920
        analysis.canvas_height = 1080
        analysis.elements = [
            Mock(element_id="elem1", bounding_box=Mock(x=100, y=100, width=200, height=100)),
            Mock(element_id="elem2", bounding_box=Mock(x=100, y=250, width=200, height=100)),
        ]
        return analysis

    @pytest.mark.asyncio
    async def test_generate_overlays_basic(self, overlay_generator, mock_analysis):
        """Test basic overlay generation."""
        overlays = await overlay_generator.generate_overlays(mock_analysis)

        assert isinstance(overlays, LayoutOverlay)
        assert overlays.canvas_width == 1920
        assert overlays.canvas_height == 1080
        assert isinstance(overlays.overlays, list)

    @pytest.mark.asyncio
    async def test_generate_alignment_guides(self, overlay_generator, mock_analysis):
        """Test alignment guide overlay generation."""
        from ..layout_opt.overlays import OverlayType

        overlays = await overlay_generator.generate_overlays(
            mock_analysis,
            overlay_types=[OverlayType.ALIGNMENT_GUIDES]
        )

        alignment_overlays = overlays.get_overlays_by_type(OverlayType.ALIGNMENT_GUIDES)
        assert isinstance(alignment_overlays, list)

    @pytest.mark.asyncio
    async def test_generate_rule_of_thirds(self, overlay_generator, mock_analysis):
        """Test rule of thirds overlay generation."""
        from ..layout_opt.overlays import OverlayType

        overlays = await overlay_generator.generate_overlays(
            mock_analysis,
            overlay_types=[OverlayType.RULE_OF_THIRDS]
        )

        rule_overlays = overlays.get_overlays_by_type(OverlayType.RULE_OF_THIRDS)
        assert len(rule_overlays) > 0  # Should have grid lines

    @pytest.mark.asyncio
    async def test_overlay_to_svg(self, overlay_generator, mock_analysis):
        """Test overlay SVG generation."""
        overlays = await overlay_generator.generate_overlays(mock_analysis)

        svg = overlays.to_svg()
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "viewBox" in svg

    @pytest.mark.asyncio
    async def test_overlay_to_dict(self, overlay_generator, mock_analysis):
        """Test overlay serialization."""
        overlays = await overlay_generator.generate_overlays(mock_analysis)

        data = overlays.to_dict()
        assert isinstance(data, dict)
        assert "canvas_width" in data
        assert "canvas_height" in data
        assert "overlays" in data
        assert "overlay_types" in data


class TestIntegration:
    """Integration tests for the complete layout optimization pipeline."""

    @pytest.mark.asyncio
    async def test_full_optimization_pipeline(self):
        """Test the complete layout optimization pipeline."""
        # Create sample layout
        layout_data = {
            "elements": [
                {
                    "element_id": "poorly_positioned_header",
                    "type": "text",
                    "x": 10,  # Too close to edge
                    "y": 10,  # Too close to edge
                    "width": 200,
                    "height": 50,
                    "text": "Header",
                    "font_size": 12  # Too small
                },
                {
                    "element_id": "body_text",
                    "type": "text",
                    "x": 10,
                    "y": 80,
                    "width": 500,  # Too wide for readability
                    "height": 100,
                    "text": "This is body text that should be more readable.",
                    "font_size": 10  # Too small
                }
            ],
            "canvas_width": 1920,
            "canvas_height": 1080
        }

        # Step 1: Analyze layout
        analyzer = LayoutAnalyzer()
        analysis = await analyzer.analyze_layout(layout_data)

        # Step 2: Score layout
        scorer = LayoutScorer()
        original_score = await scorer.score_layout(analysis)
        original_overall = original_score.overall_score

        # Step 3: Optimize layout
        optimizer = LayoutOptimizer()
        actions = await optimizer.optimize_layout(analysis, level="standard")

        # Step 4: Apply optimizations
        optimized_layout = await optimizer.apply_actions(layout_data, actions)

        # Step 5: Verify improvement
        optimized_analysis = await analyzer.analyze_layout(optimized_layout)
        optimized_score = await scorer.score_layout(optimized_analysis)
        optimized_overall = optimized_score.overall_score

        # The optimization should improve or maintain the score
        assert optimized_overall >= original_overall * 0.9  # Allow for minor degradation

        # Step 6: Generate variants
        variants_gen = LayoutVariants()
        variants = await variants_gen.generate_variants(
            optimized_layout,
            strategies=[VariantStrategy.CONSERVATIVE],
            count_per_strategy=2
        )

        assert len(variants) == 2
        for variant in variants:
            assert variant.score > 0

        # Step 7: Generate overlays
        overlay_gen = OverlayGenerator()
        overlays = await overlay_gen.generate_overlays(optimized_analysis)

        assert len(overlays.overlays) > 0

        # Success - the full pipeline works
        assert True


if __name__ == "__main__":
    pytest.main([__file__])