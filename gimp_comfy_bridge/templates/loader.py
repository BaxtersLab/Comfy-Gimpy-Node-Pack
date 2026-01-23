"""
Template loader for Comfy Gimpy Studio.

Loads complete templates including layouts, workflows, and styles.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from .registry import TemplateRegistry
from .metadata import TemplateMetadata
from .preview import load_preview

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Loader for complete template data.
    """

    def __init__(self, registry: TemplateRegistry):
        """
        Initialize the template loader.

        Args:
            registry: TemplateRegistry instance
        """
        self.registry = registry

    def load_template(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a complete template.

        Args:
            category: Template category
            name: Template name

        Returns:
            Dictionary containing all template data, or None if loading fails
        """
        logger.info(f"Loading template: {category}/{name}")

        # Get template paths
        paths = self.registry.get_template_paths(category, name)
        if not paths:
            logger.error(f"Template not found: {category}/{name}")
            return None

        # Get metadata
        metadata = self.registry.get_template_metadata(category, name)
        if not metadata:
            logger.error(f"Failed to load metadata for: {category}/{name}")
            return None

        template_data = {
            'metadata': metadata,
            'paths': paths,
            'layout': None,
            'workflow': None,
            'preview': None,
            'styles': []
        }

        # Load layout (XCF file) - for now just return the path
        template_data['layout'] = self.load_layout_xcf(paths['layout'])

        # Load workflow
        template_data['workflow'] = self.load_workflow_json(paths['workflow'])

        # Load preview
        template_data['preview'] = load_preview(paths['preview'])

        # Load styles
        template_data['styles'] = self.load_styles(paths['styles'])

        logger.info(f"Successfully loaded template: {category}/{name}")
        return template_data

    def load_layout_xcf(self, layout_path: Path) -> Optional[str]:
        """
        Load template layout (XCF file).

        For now, this is a stub that returns the path for GIMP integration.
        Real XCF loading will be implemented when GIMP integration is ready.

        Args:
            layout_path: Path to layout.xcf file

        Returns:
            Path string if file exists, None otherwise
        """
        if layout_path.exists():
            logger.debug(f"Layout file found: {layout_path}")
            return str(layout_path)
        else:
            logger.warning(f"Layout file not found: {layout_path}")
            return None

    def load_workflow_json(self, workflow_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load template workflow JSON.

        Args:
            workflow_path: Path to workflow.json file

        Returns:
            Workflow dictionary or None if loading fails
        """
        if not workflow_path.exists():
            logger.warning(f"Workflow file not found: {workflow_path}")
            return None

        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)

            # Basic validation
            if not isinstance(workflow_data, dict):
                logger.error(f"Invalid workflow format in {workflow_path}")
                return None

            logger.debug(f"Loaded workflow from: {workflow_path}")
            return workflow_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in workflow file {workflow_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load workflow from {workflow_path}: {e}")
            return None

    def load_styles(self, styles_path: Path) -> List[Dict[str, Any]]:
        """
        Load template styles.

        Args:
            styles_path: Path to styles directory

        Returns:
            List of style information dictionaries
        """
        styles = []

        if not styles_path.exists():
            logger.debug(f"Styles directory not found: {styles_path}")
            return styles

        # Load style metadata if available
        style_metadata_path = styles_path / "style_metadata.json"
        if style_metadata_path.exists():
            try:
                with open(style_metadata_path, 'r', encoding='utf-8') as f:
                    style_metadata = json.load(f)
                styles.append({
                    'type': 'metadata',
                    'data': style_metadata,
                    'path': str(style_metadata_path)
                })
            except Exception as e:
                logger.warning(f"Failed to load style metadata: {e}")

        # Find all .safetensors files
        for safetensor_file in styles_path.glob("*.safetensors"):
            styles.append({
                'type': 'safetensors',
                'name': safetensor_file.stem,
                'path': str(safetensor_file)
            })

        logger.debug(f"Loaded {len(styles)} style files from: {styles_path}")
        return styles

    def validate_template_integrity(self, category: str, name: str) -> Dict[str, bool]:
        """
        Validate that all required template files exist and are valid.

        Args:
            category: Template category
            name: Template name

        Returns:
            Dictionary mapping file types to validation status
        """
        paths = self.registry.get_template_paths(category, name)
        if not paths:
            return {'found': False}

        validation_results = {
            'found': True,
            'metadata': paths['metadata'].exists(),
            'layout': paths['layout'].exists(),
            'workflow': paths['workflow'].exists(),
            'preview': paths['preview'].exists(),
            'styles_dir': paths['styles'].exists()
        }

        # Validate metadata if it exists
        if validation_results['metadata']:
            try:
                metadata = self.registry.get_template_metadata(category, name)
                validation_results['metadata_valid'] = metadata is not None
            except Exception:
                validation_results['metadata_valid'] = False
        else:
            validation_results['metadata_valid'] = False

        # Validate workflow if it exists
        if validation_results['workflow']:
            workflow = self.load_workflow_json(paths['workflow'])
            validation_results['workflow_valid'] = workflow is not None
        else:
            validation_results['workflow_valid'] = False

        return validation_results

    def get_template_dependencies(self, category: str, name: str) -> Dict[str, List[str]]:
        """
        Get all dependencies required by a template.

        Args:
            category: Template category
            name: Template name

        Returns:
            Dictionary of dependency types and their requirements
        """
        metadata = self.registry.get_template_metadata(category, name)
        if not metadata or not metadata.dependencies:
            return {}

        return metadata.dependencies

    def prepare_template_for_gimp(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Prepare template data for GIMP integration.

        Args:
            category: Template category
            name: Template name

        Returns:
            Dictionary with GIMP-ready data or None if preparation fails
        """
        template_data = self.load_template(category, name)
        if not template_data:
            return None

        # Prepare GIMP-ready structure
        gimp_data = {
            'name': template_data['metadata'].name,
            'category': template_data['metadata'].category,
            'layout_path': template_data['layout'],
            'workflow_data': template_data['workflow'],
            'preview_data': template_data['preview'],
            'styles': template_data['styles'],
            'metadata': {
                'description': template_data['metadata'].description,
                'required_workflow': template_data['metadata'].required_workflow,
                'recommended_styles': template_data['metadata'].recommended_styles,
                'tags': template_data['metadata'].tags
            }
        }

        return gimp_data