# Comfy Gimpy Studio Templates

This directory contains template definitions for Comfy Gimpy Studio, enabling users to load pre-built layouts that integrate with AI workflows and LoRA styles.

## Directory Structure

```
templates/
├── posters/           # Poster templates (A1, A2, A3 sizes)
├── brochures/         # Brochure and flyer templates
├── business_cards/    # Business card templates
├── websites/          # Website mockup templates
├── social_media/      # Social media post templates
└── README.md         # This file
```

## Template Structure

Each template category contains individual template folders with the following structure:

```
{category}/{template_name}/
├── template.json      # Template metadata and configuration
├── preview.png        # Generated preview thumbnail
├── assets/           # Template-specific assets (fonts, images, etc.)
└── layers/           # Layer definitions and configurations
```

## Template Metadata Schema

Templates are defined using JSON metadata files that conform to a strict schema. The schema ensures consistency and enables automated validation.

### Schema Files

- `template_schema.json`: Complete JSON Schema definition for template metadata
- `template_validator.py`: Python script to validate templates against the schema

### Running Validation

To validate a single template:
```bash
python template_validator.py . posters/modern_business_poster.json
```

To validate all templates:
```bash
python template_validator.py .
```

### Schema Overview

The template schema includes the following key sections:

#### Core Metadata
- `name`: Human-readable template name
- `description`: Detailed description
- `category`: Must match the containing directory
- `version`: Semantic versioning (e.g., "1.0.0")
- `author`: Template creator
- `tags`: Array of search/filter tags

#### Canvas Configuration
- `dimensions`: Width, height, and DPI settings
- `background_color`: Default background color

#### Layer Definitions
- `layers`: Array of layer objects with properties:
  - `name`: Layer identifier
  - `type`: Layer type (text, image, shape, background, group)
  - `visible`: Layer visibility
  - `opacity`: Layer opacity (0-100)
  - `blend_mode`: GIMP blend mode
  - `position`: Layer position and dimensions

#### Content Placeholders
- `placeholders`: User-editable content points:
  - `id`: Unique identifier
  - `type`: Content type (text, image, logo, background_image)
  - `layer_name`: Associated layer
  - `label`: User-friendly label
  - `constraints`: Validation rules (max length, formats, dimensions)

#### Workflow Integration
- `workflow_bindings`: ComfyUI workflow connections:
  - `default_workflow`: Primary workflow name
  - `alternative_workflows`: Backup workflow options
  - `parameter_mappings`: Template-to-workflow parameter mapping

#### Style and Dependencies
- `style_requirements`: Compatible LoRA styles and models
- `dependencies`: Required workflows, models, and fonts

## Template Categories

### Posters
- Event posters
- Promotional posters
- Artistic posters
- Informational posters

### Brochures
- Tri-fold brochures
- Bi-fold brochures
- Flyers
- Newsletters

### Business Cards
- Standard business cards
- Creative business cards
- Digital business cards

### Websites
- Landing page mockups
- Portfolio layouts
- Blog templates
- E-commerce pages

### Social Media
- Instagram posts
- Facebook covers
- Twitter headers
- LinkedIn banners

## Template Development Tools

The templates directory includes several Python modules for template development and management:

### Core Modules

- `template_schema.json`: JSON Schema definition for template metadata validation
- `template_validator.py`: Validates template files against the schema
- `template_preview_generator.py`: Generates preview thumbnails for templates
- `template_loader.py`: Loads and manages template metadata for GIMP integration
- `template_workflow_binding.py`: Manages bindings between templates and ComfyUI workflows
- `template_categorization.py`: Provides categorization, tagging, and search functionality

### Usage Examples

#### Validate Templates
```bash
# Validate a single template
python template_validator.py . posters/modern_business_poster.json

# Validate all templates
python template_validator.py .
```

#### Generate Previews
```bash
# Generate preview for a specific template
python template_preview_generator.py . posters/modern_business_poster.json

# Generate previews for all templates
python template_preview_generator.py .
```

#### Load and Search Templates
```bash
# List all templates
python template_loader.py . list

# Load template details
python template_loader.py . load posters/modern_business_poster

# Search templates
python template_categorization.py . search business
```

#### Check Workflow Requirements
```bash
# Show workflow requirements for a template
python template_workflow_binding.py . requirements posters/modern_business_poster
```

## Development Notes

- Templates are loaded dynamically by the GIMP plugin
- Preview generation uses ComfyUI workflows for realistic thumbnails
- Templates support versioning and compatibility checking
- All templates must validate against `template_schema.json` before distribution
- Use `template_validator.py` to check template validity during development
- Schema validation ensures consistent structure across all templates
- Custom validation rules check layer references and workflow dependencies