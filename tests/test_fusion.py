"""
Tests for Fusion Engine (Phase 8)
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from gimp_comfy_bridge.fusion_engine import (
    FusionEngine,
    FusionMode,
    FusionLayer,
    FusionResult,
    FusionConfig
)
from shared.types import FusionInfo, LayerInfo


class TestFusionLayer:
    """Test the FusionLayer class."""

    def test_layer_creation(self):
        """Test creating a fusion layer."""
        # Create mock image data
        image_data = np.random.rand(100, 100, 3)

        layer = FusionLayer(
            id="layer1",
            name="Test Layer",
            image_data=image_data,
            opacity=0.8,
            blend_mode="normal",
            position=(10, 20)
        )

        assert layer.id == "layer1"
        assert layer.name == "Test Layer"
        assert layer.opacity == 0.8
        assert layer.blend_mode == "normal"
        assert layer.position == (10, 20)
        assert layer.visible is True

    def test_layer_with_mask(self):
        """Test layer with mask."""
        image_data = np.random.rand(50, 50, 4)
        mask_data = np.random.rand(50, 50)

        layer = FusionLayer(
            id="masked_layer",
            name="Masked Layer",
            image_data=image_data,
            mask=mask_data,
            opacity=1.0
        )

        assert layer.mask is not None
        assert layer.mask.shape == (50, 50)

    def test_layer_to_dict(self):
        """Test converting layer to dictionary."""
        image_data = np.random.rand(10, 10, 3)
        layer = FusionLayer("test", "Test", image_data)

        layer_dict = layer.to_dict()
        assert layer_dict["id"] == "test"
        assert layer_dict["name"] == "Test"
        assert layer_dict["opacity"] == 1.0
        assert layer_dict["visible"] is True


class TestFusionConfig:
    """Test the FusionConfig class."""

    def test_config_creation(self):
        """Test creating a fusion configuration."""
        config = FusionConfig(
            mode=FusionMode.STACK,
            output_format="PNG",
            quality=95,
            background_color=(255, 255, 255, 255)
        )

        assert config.mode == FusionMode.STACK
        assert config.output_format == "PNG"
        assert config.quality == 95
        assert config.background_color == (255, 255, 255, 255)

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = FusionConfig()

        assert config.mode == FusionMode.STACK
        assert config.output_format == "PNG"
        assert config.quality == 90
        assert config.background_color == (0, 0, 0, 0)  # Transparent

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = FusionConfig(mode=FusionMode.MASK, quality=85)

        config_dict = config.to_dict()
        assert config_dict["mode"] == "mask"
        assert config_dict["quality"] == 85


class TestFusionResult:
    """Test the FusionResult class."""

    def test_result_creation(self):
        """Test creating a fusion result."""
        output_data = np.random.rand(200, 200, 4)

        result = FusionResult(
            success=True,
            output_data=output_data,
            metadata={"format": "RGBA", "size": (200, 200)},
            processing_time=1.5
        )

        assert result.success is True
        assert result.output_data.shape == (200, 200, 4)
        assert result.metadata["format"] == "RGBA"
        assert result.processing_time == 1.5

    def test_result_failure(self):
        """Test failed fusion result."""
        result = FusionResult(
            success=False,
            error_message="Fusion failed",
            processing_time=0.5
        )

        assert result.success is False
        assert result.error_message == "Fusion failed"
        assert result.output_data is None


class TestFusionEngine:
    """Test the fusion engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = FusionEngine()

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        assert self.engine.max_image_size == (4096, 4096)
        assert self.engine.supported_formats == ["PNG", "JPEG", "TIFF", "BMP"]

    def test_validate_image_data(self):
        """Test image data validation."""
        # Valid image data
        valid_data = np.random.rand(100, 100, 3)
        assert self.engine._validate_image_data(valid_data) is True

        # Invalid dimensions
        invalid_data = np.random.rand(100)  # 1D array
        assert self.engine._validate_image_data(invalid_data) is False

        # Too large
        large_data = np.random.rand(5000, 5000, 3)
        assert self.engine._validate_image_data(large_data) is False

    def test_stack_mode_fusion(self):
        """Test stack mode fusion."""
        # Create test layers
        layer1_data = np.ones((50, 50, 4)) * 255  # White
        layer1_data[:, :, 3] = 255  # Fully opaque

        layer2_data = np.zeros((50, 50, 4))  # Black
        layer2_data[:, :, 3] = 128  # Semi-transparent

        layer1 = FusionLayer("layer1", "White Layer", layer1_data, opacity=1.0)
        layer2 = FusionLayer("layer2", "Black Layer", layer2_data, opacity=0.5)

        config = FusionConfig(mode=FusionMode.STACK)

        result = self.engine.fuse_layers([layer1, layer2], config)

        assert result.success is True
        assert result.output_data is not None
        assert result.output_data.shape == (50, 50, 4)

    def test_mask_mode_fusion(self):
        """Test mask mode fusion."""
        # Create base layer
        base_data = np.random.rand(50, 50, 4) * 255

        # Create mask layer (grayscale)
        mask_data = np.ones((50, 50)) * 128  # Semi-transparent mask

        base_layer = FusionLayer("base", "Base", base_data)
        mask_layer = FusionLayer("mask", "Mask", mask_data, opacity=1.0)

        config = FusionConfig(mode=FusionMode.MASK)

        result = self.engine.fuse_layers([base_layer, mask_layer], config)

        assert result.success is True
        assert result.output_data.shape == (50, 50, 4)

    def test_blend_mode_fusion(self):
        """Test blend mode fusion."""
        layer1_data = np.ones((50, 50, 4)) * 128  # 50% gray
        layer2_data = np.ones((50, 50, 4)) * 64   # 25% gray

        layer1 = FusionLayer("layer1", "Gray 50%", layer1_data, blend_mode="multiply")
        layer2 = FusionLayer("layer2", "Gray 25%", layer2_data, blend_mode="screen")

        config = FusionConfig(mode=FusionMode.BLEND)

        result = self.engine.fuse_layers([layer1, layer2], config)

        assert result.success is True
        assert result.output_data is not None

    def test_layer_positioning(self):
        """Test layer positioning in fusion."""
        # Create layers with different positions
        small_layer_data = np.ones((20, 20, 4)) * 255
        large_layer_data = np.zeros((100, 100, 4))

        small_layer = FusionLayer(
            "small", "Small Layer", small_layer_data,
            position=(10, 10)
        )
        large_layer = FusionLayer(
            "large", "Large Layer", large_layer_data,
            position=(0, 0)
        )

        config = FusionConfig(mode=FusionMode.STACK)

        result = self.engine.fuse_layers([large_layer, small_layer], config)

        assert result.success is True
        assert result.output_data.shape[0] >= 30  # At least 10 + 20
        assert result.output_data.shape[1] >= 30

    def test_opacity_handling(self):
        """Test opacity handling in fusion."""
        layer_data = np.ones((50, 50, 4)) * 255

        # Fully opaque layer
        opaque_layer = FusionLayer("opaque", "Opaque", layer_data, opacity=1.0)

        # Semi-transparent layer
        transparent_layer = FusionLayer("transparent", "Transparent", layer_data, opacity=0.5)

        config = FusionConfig(mode=FusionMode.STACK)

        result = self.engine.fuse_layers([opaque_layer, transparent_layer], config)

        assert result.success is True
        # The result should reflect the opacity blending

    def test_format_conversion(self):
        """Test output format conversion."""
        layer_data = np.random.rand(50, 50, 4) * 255

        layer = FusionLayer("test", "Test", layer_data)

        # Test PNG output
        config_png = FusionConfig(output_format="PNG")
        result_png = self.engine.fuse_layers([layer], config_png)
        assert result_png.success is True

        # Test JPEG output (should convert to RGB)
        config_jpeg = FusionConfig(output_format="JPEG")
        result_jpeg = self.engine.fuse_layers([layer], config_jpeg)
        assert result_jpeg.success is True
        # JPEG should be RGB (3 channels)
        assert result_jpeg.output_data.shape[2] == 3

    def test_error_handling(self):
        """Test error handling in fusion."""
        # Empty layer list
        config = FusionConfig()
        result = self.engine.fuse_layers([], config)

        assert result.success is False
        assert "No layers provided" in result.error_message

        # Invalid layer data
        invalid_layer = FusionLayer("invalid", "Invalid", np.array([]))
        result = self.engine.fuse_layers([invalid_layer], config)

        assert result.success is False

    def test_fusion_info_conversion(self):
        """Test converting fusion result to FusionInfo."""
        output_data = np.random.rand(100, 100, 4)
        result = FusionResult(
            success=True,
            output_data=output_data,
            metadata={"size": (100, 100)},
            processing_time=2.0
        )

        fusion_info = self.engine._result_to_fusion_info(result, "test_fusion")
        assert isinstance(fusion_info, FusionInfo)
        assert fusion_info.id == "test_fusion"
        assert fusion_info.success is True
        assert fusion_info.processing_time == 2.0

    @patch('PIL.Image.fromarray')
    def test_pil_image_conversion(self, mock_fromarray):
        """Test PIL Image conversion."""
        # Mock PIL Image
        mock_image = Mock()
        mock_fromarray.return_value = mock_image

        layer_data = np.random.rand(50, 50, 4) * 255
        layer = FusionLayer("test", "Test", layer_data)

        config = FusionConfig(output_format="PNG")

        # This should trigger PIL conversion
        result = self.engine.fuse_layers([layer], config)

        # Verify PIL was used for format conversion
        if config.output_format != "RAW":
            mock_fromarray.assert_called()

    def test_memory_efficiency(self):
        """Test memory efficiency with large images."""
        # Create moderately large test data
        large_data = np.random.rand(1000, 1000, 4).astype(np.float32)

        layer = FusionLayer("large", "Large Layer", large_data)

        config = FusionConfig(mode=FusionMode.STACK)

        result = self.engine.fuse_layers([layer], config)

        assert result.success is True
        # Should handle large images without excessive memory usage
        assert result.output_data.shape[0] <= 1000
        assert result.output_data.shape[1] <= 1000