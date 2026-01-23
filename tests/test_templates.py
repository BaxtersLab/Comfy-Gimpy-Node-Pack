"""
Tests for Template Engine (Phase 1)
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from gimp_comfy_bridge.templates import TemplateRegistry, TemplateLoader
from shared.types import Template


class TestTemplateRegistry:
    """Test the template registry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = TemplateRegistry()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_registry_initialization(self):
        """Test registry initializes correctly."""
        assert self.registry.templates == {}
        assert self.registry.categories == []

    def test_register_template(self):
        """Test registering a template."""
        template = Template(
            id="test_template",
            name="Test Template",
            category="test",
            description="A test template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        self.registry.register_template(template)
        assert "test_template" in self.registry.templates
        assert self.registry.templates["test_template"] == template

    def test_get_template(self):
        """Test retrieving a template."""
        template = Template(
            id="test_template",
            name="Test Template",
            category="test",
            description="A test template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        self.registry.register_template(template)
        retrieved = self.registry.get_template("test_template")
        assert retrieved == template

    def test_get_template_not_found(self):
        """Test retrieving a non-existent template."""
        with pytest.raises(ValueError, match="Template not found"):
            self.registry.get_template("nonexistent")

    def test_list_templates_by_category(self):
        """Test listing templates by category."""
        template1 = Template(
            id="template1",
            name="Template 1",
            category="business",
            description="Business template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        template2 = Template(
            id="template2",
            name="Template 2",
            category="social",
            description="Social template",
            dimensions=(1080, 1080),
            layers=[],
            placeholders=[]
        )

        self.registry.register_template(template1)
        self.registry.register_template(template2)

        business_templates = self.registry.list_templates_by_category("business")
        assert len(business_templates) == 1
        assert business_templates[0].id == "template1"

    def test_get_categories(self):
        """Test getting available categories."""
        template1 = Template(
            id="template1",
            name="Template 1",
            category="business",
            description="Business template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        template2 = Template(
            id="template2",
            name="Template 2",
            category="social",
            description="Social template",
            dimensions=(1080, 1080),
            layers=[],
            placeholders=[]
        )

        self.registry.register_template(template1)
        self.registry.register_template(template2)

        categories = self.registry.get_categories()
        assert "business" in categories
        assert "social" in categories


class TestTemplateLoader:
    """Test the template loader functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = TemplateLoader()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_template_from_directory(self):
        """Test loading a template from a directory."""
        # Create a mock template directory structure
        template_dir = Path(self.temp_dir) / "test_template"
        template_dir.mkdir()

        # Create template.json
        template_data = {
            "id": "test_template",
            "name": "Test Template",
            "category": "test",
            "description": "A test template",
            "dimensions": [1920, 1080],
            "layers": [],
            "placeholders": []
        }

        with open(template_dir / "template.json", "w") as f:
            json.dump(template_data, f)

        # Load the template
        template = self.loader.load_template_from_directory(template_dir)

        assert template.id == "test_template"
        assert template.name == "Test Template"
        assert template.category == "test"
        assert template.dimensions == (1920, 1080)

    def test_load_template_invalid_json(self):
        """Test loading a template with invalid JSON."""
        template_dir = Path(self.temp_dir) / "invalid_template"
        template_dir.mkdir()

        # Create invalid JSON
        with open(template_dir / "template.json", "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            self.loader.load_template_from_directory(template_dir)

    def test_load_template_missing_file(self):
        """Test loading a template with missing template.json."""
        template_dir = Path(self.temp_dir) / "missing_template"
        template_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            self.loader.load_template_from_directory(template_dir)

    @patch('gimp_comfy_bridge.templates.Path')
    def test_scan_templates_directory(self, mock_path):
        """Test scanning a templates directory."""
        # Mock the directory structure
        mock_templates_dir = Mock()
        mock_template_dir = Mock()
        mock_template_dir.is_dir.return_value = True
        mock_template_dir.name = "test_template"
        mock_templates_dir.iterdir.return_value = [mock_template_dir]

        mock_path.return_value = mock_templates_dir

        with patch.object(self.loader, 'load_template_from_directory') as mock_load:
            mock_load.return_value = Template(
                id="test_template",
                name="Test Template",
                category="test",
                description="A test template",
                dimensions=(1920, 1080),
                layers=[],
                placeholders=[]
            )

            templates = self.loader.scan_templates_directory(Path("/fake/path"))

            assert len(templates) == 1
            assert templates[0].id == "test_template"
            mock_load.assert_called_once()

    def test_validate_template_structure(self):
        """Test template structure validation."""
        # Valid template
        valid_template = Template(
            id="valid_template",
            name="Valid Template",
            category="test",
            description="A valid template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        assert self.loader.validate_template_structure(valid_template)

        # Invalid template (missing required fields)
        invalid_template = Template(
            id="",  # Empty ID
            name="Invalid Template",
            category="test",
            description="An invalid template",
            dimensions=(1920, 1080),
            layers=[],
            placeholders=[]
        )

        assert not self.loader.validate_template_structure(invalid_template)