"""
Template Saver for Comfy Gimpy Studio (Phase 12)

Saves generated templates to the proper directory structure with
layout files, workflows, metadata, and previews.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import shutil
from datetime import datetime

from ..shared.config import Config

logger = logging.getLogger(__name__)


class TemplateSaver:
    """Saves generated templates to disk."""

    def __init__(self, config: Config):
        """
        Initialize the template saver.

        Args:
            config: Application configuration
        """
        self.config = config
        self.templates_base_path = Path(config.get("paths.templates", "templates"))

        # Ensure base directory exists
        self.templates_base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Template saver initialized with base path: {self.templates_base_path}")

    def save_template(self, layout_data: Dict[str, Any],
                     metadata: Any,
                     workflow_data: Dict[str, Any],
                     previews: List[Dict[str, Any]],
                     category: str) -> Path:
        """
        Save a complete template.

        Args:
            layout_data: Generated layout data
            metadata: Template metadata object
            workflow_data: Workflow data dictionary
            previews: List of preview data
            category: Template category

        Returns:
            Path to saved template directory
        """
        try:
            # Generate template directory name
            template_name = self._generate_template_name(metadata)
            template_path = self._get_template_path(category, template_name)

            # Create directory structure
            template_path.mkdir(parents=True, exist_ok=True)

            # Save layout
            self._save_layout(layout_data, template_path)

            # Save metadata
            self._save_metadata(metadata, template_path)

            # Save workflow
            if workflow_data:
                self._save_workflow(workflow_data, template_path)

            # Save previews
            self._save_previews(previews, template_path)

            # Create additional files
            self._create_additional_files(template_path)

            logger.info(f"Template saved to: {template_path}")
            return template_path

        except Exception as e:
            logger.error(f"Template saving failed: {e}")
            raise

    def _generate_template_name(self, metadata: Any) -> str:
        """
        Generate a unique template name.

        Args:
            metadata: Template metadata

        Returns:
            Generated template name
        """
        base_name = getattr(metadata, 'name', 'Generated Template')

        # Clean the name for filesystem use
        clean_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_').lower()

        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template_name = f"{clean_name}_{timestamp}"

        return template_name

    def _get_template_path(self, category: str, template_name: str) -> Path:
        """
        Get the full path for a template.

        Args:
            category: Template category
            template_name: Template name

        Returns:
            Full template path
        """
        # Clean category name
        clean_category = category.replace('_', ' ').title().replace(' ', '')

        return self.templates_base_path / clean_category / template_name

    def _save_layout(self, layout_data: Dict[str, Any], template_path: Path):
        """
        Save layout data.

        Args:
            layout_data: Layout data dictionary
            template_path: Template directory path
        """
        # Save as JSON for development (would be XCF in production)
        layout_file = template_path / "layout.json"
        with open(layout_file, 'w', encoding='utf-8') as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)

        # In production, this would export to XCF format
        # self._export_to_xcf(layout_data, template_path / "layout.xcf")

        logger.debug(f"Layout saved to: {layout_file}")

    def _save_metadata(self, metadata: Any, template_path: Path):
        """
        Save template metadata.

        Args:
            metadata: Template metadata object
            template_path: Template directory path
        """
        metadata_dict = metadata.to_dict() if hasattr(metadata, 'to_dict') else metadata

        metadata_file = template_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        logger.debug(f"Metadata saved to: {metadata_file}")

    def _save_workflow(self, workflow_data: Dict[str, Any], template_path: Path):
        """
        Save workflow data.

        Args:
            workflow_data: Workflow data dictionary
            template_path: Template directory path
        """
        workflow_file = template_path / "workflow.json"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Workflow saved to: {workflow_file}")

    def _save_previews(self, previews: List[Dict[str, Any]], template_path: Path):
        """
        Save preview images.

        Args:
            previews: List of preview data
            template_path: Template directory path
        """
        for preview in previews:
            preview_path = Path(preview.get("path", ""))
            if preview_path.exists():
                # Copy preview to template directory
                filename = preview.get("filename", f"preview_{preview.get('type', 'unknown')}.png")
                dest_path = template_path / filename

                try:
                    shutil.copy2(preview_path, dest_path)
                    logger.debug(f"Preview copied to: {dest_path}")
                except Exception as e:
                    logger.error(f"Failed to copy preview {preview_path}: {e}")

    def _create_additional_files(self, template_path: Path):
        """
        Create additional template files.

        Args:
            template_path: Template directory path
        """
        # Create README
        readme_content = self._generate_readme(template_path)
        readme_file = template_path / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        # Create .gimptemplate file for GIMP integration
        gimp_template = self._generate_gimp_template(template_path)
        gimp_file = template_path / ".gimptemplate"
        with open(gimp_file, 'w', encoding='utf-8') as f:
            f.write(gimp_template)

        logger.debug("Additional template files created")

    def _generate_readme(self, template_path: Path) -> str:
        """
        Generate README content for template.

        Args:
            template_path: Template directory path

        Returns:
            README content
        """
        # Load metadata
        metadata_file = template_path / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass

        name = metadata.get("name", "Generated Template")
        description = metadata.get("description", "AI-generated template")
        category = metadata.get("category", "general")
        tags = metadata.get("tags", [])

        readme = f"""# {name}

{description}

## Category
{category.title()}

## Tags
{', '.join(tags) if tags else 'None'}

## Files
- `layout.json` - Template layout definition
- `metadata.json` - Template metadata
- `workflow.json` - ComfyUI workflow (if applicable)
- `preview.png` - Template preview image
- `thumbnail.png` - Template thumbnail (if available)

## Usage
1. Open the layout file in GIMP
2. Load the associated workflow in ComfyUI (if applicable)
3. Customize colors, fonts, and content as needed

## Generated by
Comfy Gimpy Studio (Phase 12 - AI-Assisted Template Generation)
"""

        return readme

    def _generate_gimp_template(self, template_path: Path) -> str:
        """
        Generate GIMP template configuration.

        Args:
            template_path: Template directory path

        Returns:
            GIMP template content
        """
        # Load metadata
        metadata_file = template_path / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass

        name = metadata.get("name", "Generated Template")
        width, height = metadata.get("dimensions", [1920, 1080])

        # GIMP template format
        template = f"""# GIMP Template
Name: {name}
Width: {width}
Height: {height}
Unit: pixels
Xresolution: 72
Yresolution: 72
Resolution-unit: inches
Image-type: RGB
Fill-type: Background
Comment: Generated by Comfy Gimpy Studio
"""

        return template

    def save_template_package(self, template_path: Path,
                            output_path: Optional[Path] = None) -> Path:
        """
        Save template as a compressed package.

        Args:
            template_path: Template directory path
            output_path: Optional output path

        Returns:
            Path to package file
        """
        if output_path is None:
            template_name = template_path.name
            output_path = template_path.parent / f"{template_name}.zip"

        try:
            import zipfile

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in template_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(template_path.parent)
                        zipf.write(file_path, arcname)

            logger.info(f"Template package saved to: {output_path}")
            return output_path

        except ImportError:
            logger.warning("zipfile not available, skipping package creation")
            return template_path
        except Exception as e:
            logger.error(f"Package creation failed: {e}")
            return template_path

    def validate_template(self, template_path: Path) -> List[str]:
        """
        Validate a saved template.

        Args:
            template_path: Template directory path

        Returns:
            List of validation errors
        """
        errors = []

        # Check required files
        required_files = ["layout.json", "metadata.json"]
        for filename in required_files:
            if not (template_path / filename).exists():
                errors.append(f"Missing required file: {filename}")

        # Check metadata
        metadata_file = template_path / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                required_fields = ["name", "category", "dimensions"]
                for field in required_fields:
                    if field not in metadata:
                        errors.append(f"Missing metadata field: {field}")

            except Exception as e:
                errors.append(f"Invalid metadata file: {e}")

        # Check layout
        layout_file = template_path / "layout.json"
        if layout_file.exists():
            try:
                with open(layout_file, 'r', encoding='utf-8') as f:
                    layout = json.load(f)

                if "elements" not in layout:
                    errors.append("Layout missing elements array")

                if "dimensions" not in layout:
                    errors.append("Layout missing dimensions")

            except Exception as e:
                errors.append(f"Invalid layout file: {e}")

        return errors

    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List saved templates.

        Args:
            category: Optional category filter

        Returns:
            List of template information
        """
        templates = []

        search_path = self.templates_base_path
        if category:
            clean_category = category.replace('_', ' ').title().replace(' ', '')
            search_path = search_path / clean_category

        if not search_path.exists():
            return templates

        for category_dir in search_path.glob("*"):
            if not category_dir.is_dir():
                continue

            for template_dir in category_dir.glob("*"):
                if not template_dir.is_dir():
                    continue

                # Check if it's a valid template
                if (template_dir / "metadata.json").exists():
                    try:
                        with open(template_dir / "metadata.json", 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        template_info = {
                            "path": str(template_dir),
                            "name": metadata.get("name", template_dir.name),
                            "category": metadata.get("category", category_dir.name),
                            "created": metadata.get("created_at", ""),
                            "has_workflow": (template_dir / "workflow.json").exists(),
                            "has_preview": (template_dir / "preview.png").exists()
                        }
                        templates.append(template_info)

                    except Exception as e:
                        logger.warning(f"Could not read template metadata: {template_dir} - {e}")

        return templates

    def delete_template(self, template_path: Union[str, Path]) -> bool:
        """
        Delete a template.

        Args:
            template_path: Template directory path

        Returns:
            True if deleted successfully
        """
        template_path = Path(template_path)

        try:
            if template_path.exists() and template_path.is_dir():
                shutil.rmtree(template_path)
                logger.info(f"Template deleted: {template_path}")
                return True
            else:
                logger.warning(f"Template not found: {template_path}")
                return False

        except Exception as e:
            logger.error(f"Template deletion failed: {e}")
            return False