#!/usr/bin/env python3
"""
Template Metadata Validator for Comfy Gimpy Studio

Validates template metadata files against the JSON schema.
Ensures all templates conform to the required structure and constraints.
"""

import json
import jsonschema
import pathlib
import sys
from typing import Dict, List, Optional, Tuple


class TemplateValidator:
    """Validates template metadata files against the schema."""

    def __init__(self, schema_path: pathlib.Path):
        """Initialize validator with schema file."""
        self.schema_path = schema_path
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict:
        """Load the JSON schema from file."""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")

    def validate_template(self, template_path: pathlib.Path) -> Tuple[bool, List[str]]:
        """
        Validate a single template metadata file.

        Args:
            template_path: Path to the template JSON file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # Load template data
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            # Validate against schema
            jsonschema.validate(instance=template_data, schema=self.schema)

            # Additional custom validations
            custom_errors = self._validate_custom_rules(template_data, template_path)
            return len(custom_errors) == 0, custom_errors

        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except jsonschema.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
        except Exception as e:
            return False, [f"Validation error: {e}"]

    def _validate_custom_rules(self, template_data: Dict, template_path: pathlib.Path) -> List[str]:
        """Perform custom validation rules beyond JSON schema."""
        errors = []

        # Check that category matches directory structure
        expected_category = template_path.parent.name
        actual_category = template_data.get('category')
        if actual_category != expected_category:
            errors.append(f"Category mismatch: expected '{expected_category}', got '{actual_category}'")

        # Validate layer references in placeholders
        layer_names = {layer['name'] for layer in template_data.get('layers', [])}
        for placeholder in template_data.get('placeholders', []):
            layer_name = placeholder.get('layer_name')
            if layer_name and layer_name not in layer_names:
                errors.append(f"Placeholder '{placeholder.get('id')}' references unknown layer '{layer_name}'")

        # Validate workflow dependencies
        required_workflows = template_data.get('dependencies', {}).get('workflows', [])
        default_workflow = template_data.get('workflow_bindings', {}).get('default_workflow')
        if default_workflow and default_workflow not in required_workflows:
            errors.append(f"Default workflow '{default_workflow}' not listed in dependencies")

        # Check dimension constraints
        dimensions = template_data.get('dimensions', {})
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)
        if width > 4096 or height > 4096:
            errors.append("Template dimensions exceed recommended maximum (4096x4096)")

        return errors

    def validate_all_templates(self, templates_dir: pathlib.Path) -> Dict[str, List[str]]:
        """
        Validate all template files in the templates directory.

        Args:
            templates_dir: Root templates directory

        Returns:
            Dictionary mapping template paths to their validation errors
        """
        validation_results = {}

        # Find all JSON files in category subdirectories
        for category_dir in templates_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                for template_file in category_dir.glob('*.json'):
                    is_valid, errors = self.validate_template(template_file)
                    if not is_valid:
                        validation_results[str(template_file.relative_to(templates_dir))] = errors

        return validation_results

    def get_template_summary(self, template_path: pathlib.Path) -> Optional[Dict]:
        """Get a summary of template metadata for quick inspection."""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                'name': data.get('name'),
                'category': data.get('category'),
                'version': data.get('version'),
                'placeholders_count': len(data.get('placeholders', [])),
                'layers_count': len(data.get('layers', [])),
                'dimensions': data.get('dimensions'),
                'author': data.get('author')
            }
        except Exception:
            return None


def main():
    """Command-line interface for template validation."""
    if len(sys.argv) < 2:
        print("Usage: python template_validator.py <templates_dir> [template_file]")
        sys.exit(1)

    templates_dir = pathlib.Path(sys.argv[1])
    schema_path = templates_dir / 'template_schema.json'

    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        sys.exit(1)

    validator = TemplateValidator(schema_path)

    if len(sys.argv) == 3:
        # Validate single template
        template_path = pathlib.Path(sys.argv[2])
        is_valid, errors = validator.validate_template(template_path)

        if is_valid:
            print(f"✓ Template {template_path} is valid")
            summary = validator.get_template_summary(template_path)
            if summary:
                print("Template Summary:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
        else:
            print(f"✗ Template {template_path} has errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    else:
        # Validate all templates
        results = validator.validate_all_templates(templates_dir)

        if not results:
            print("✓ All templates are valid")
        else:
            print(f"✗ Found {len(results)} invalid templates:")
            for template_path, errors in results.items():
                print(f"\n{template_path}:")
                for error in errors:
                    print(f"  - {error}")
            sys.exit(1)


if __name__ == '__main__':
    main()