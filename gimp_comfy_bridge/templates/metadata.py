"""
Template metadata loading and validation for Comfy Gimpy Studio.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """
    Complete metadata for a template.
    """
    name: str
    category: str
    description: str
    required_workflow: str
    recommended_styles: List[str]
    tags: List[str]
    version: Optional[str] = None
    author: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None
    dependencies: Optional[Dict[str, Any]] = None


def load_metadata(metadata_path: Path) -> TemplateMetadata:
    """
    Load template metadata from JSON file.

    Args:
        metadata_path: Path to metadata.json file

    Returns:
        TemplateMetadata object

    Raises:
        FileNotFoundError: If metadata file doesn't exist
        ValueError: If metadata is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate the metadata
        validate_metadata(data)

        # Create and return metadata object
        return TemplateMetadata(
            name=data.get('name', ''),
            category=data.get('category', ''),
            description=data.get('description', ''),
            required_workflow=data.get('required_workflow', ''),
            recommended_styles=data.get('recommended_styles', []),
            tags=data.get('tags', []),
            version=data.get('version'),
            author=data.get('author'),
            dimensions=data.get('dimensions'),
            dependencies=data.get('dependencies')
        )

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in metadata file {metadata_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load metadata from {metadata_path}: {e}")


def validate_metadata(data: Dict[str, Any]) -> None:
    """
    Validate template metadata structure.

    Args:
        data: Metadata dictionary to validate

    Raises:
        ValueError: If metadata is invalid
    """
    required_fields = ['name', 'category', 'description', 'required_workflow']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]

    if missing_fields:
        raise ValueError(f"Missing required metadata fields: {missing_fields}")

    # Validate field types
    if not isinstance(data['name'], str) or not data['name'].strip():
        raise ValueError("Template name must be a non-empty string")

    if not isinstance(data['category'], str) or not data['category'].strip():
        raise ValueError("Template category must be a non-empty string")

    if not isinstance(data['description'], str) or not data['description'].strip():
        raise ValueError("Template description must be a non-empty string")

    if not isinstance(data['required_workflow'], str) or not data['required_workflow'].strip():
        raise ValueError("Required workflow must be a non-empty string")

    # Validate optional fields
    if 'recommended_styles' in data:
        if not isinstance(data['recommended_styles'], list):
            raise ValueError("Recommended styles must be a list")
        if not all(isinstance(style, str) for style in data['recommended_styles']):
            raise ValueError("All recommended styles must be strings")

    if 'tags' in data:
        if not isinstance(data['tags'], list):
            raise ValueError("Tags must be a list")
        if not all(isinstance(tag, str) for tag in data['tags']):
            raise ValueError("All tags must be strings")

    if 'version' in data and not isinstance(data['version'], str):
        raise ValueError("Version must be a string")

    if 'author' in data and not isinstance(data['author'], str):
        raise ValueError("Author must be a string")

    if 'dimensions' in data:
        if not isinstance(data['dimensions'], dict):
            raise ValueError("Dimensions must be a dictionary")
        required_dim_fields = ['width', 'height']
        for field in required_dim_fields:
            if field not in data['dimensions']:
                raise ValueError(f"Dimensions must include '{field}'")
            if not isinstance(data['dimensions'][field], int) or data['dimensions'][field] <= 0:
                raise ValueError(f"Dimension '{field}' must be a positive integer")

    logger.debug(f"Validated metadata for template: {data.get('name')}")


def save_metadata(metadata: TemplateMetadata, metadata_path: Path) -> None:
    """
    Save template metadata to JSON file.

    Args:
        metadata: TemplateMetadata object to save
        metadata_path: Path where to save the metadata
    """
    data = {
        'name': metadata.name,
        'category': metadata.category,
        'description': metadata.description,
        'required_workflow': metadata.required_workflow,
        'recommended_styles': metadata.recommended_styles,
        'tags': metadata.tags,
    }

    # Add optional fields if they exist
    if metadata.version:
        data['version'] = metadata.version
    if metadata.author:
        data['author'] = metadata.author
    if metadata.dimensions:
        data['dimensions'] = metadata.dimensions
    if metadata.dependencies:
        data['dependencies'] = metadata.dependencies

    # Ensure parent directory exists
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.debug(f"Saved metadata for template: {metadata.name}")