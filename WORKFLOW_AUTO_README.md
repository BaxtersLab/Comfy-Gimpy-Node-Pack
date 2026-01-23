# Comfy Gimpy Studio - Workflow Auto-Generation System

## Overview

The Workflow Auto-Generation System is Phase 7 of Comfy Gimpy Studio, providing intelligent automatic generation of ComfyUI workflows from templates and styles. This system enables users to create complex ComfyUI workflows without manual node placement and connection.

## Features

- **Template-Based Generation**: Build workflows from predefined templates
- **Style Integration**: Apply visual/audio processing styles to workflows
- **Rule-Based Modifications**: Intelligent workflow modifications based on conditions
- **Comprehensive Validation**: Ensure workflow integrity and compatibility
- **Performance Caching**: Fast workflow generation with intelligent caching
- **Web API Integration**: RESTful API for web interface integration

## Architecture

### Core Components

#### 1. WorkflowBuilder (`gimp_comfy_bridge/workflow_auto/builder.py`)
Main orchestration component that coordinates template loading, style application, rule processing, and final workflow assembly.

**Key Methods:**
- `build_workflow()`: Main workflow building method
- `get_available_templates()`: List available workflow templates
- `get_available_styles()`: List available workflow styles

#### 2. NodeGraph (`gimp_comfy_bridge/workflow_auto/graph.py`)
Represents ComfyUI workflows as graphs with nodes and connections, providing topological sorting and cycle detection.

**Key Features:**
- Node and connection management
- Topological ordering for execution
- Cycle detection and validation

#### 3. RuleEngine (`gimp_comfy_bridge/workflow_auto/rules.py`)
Applies intelligent modifications to workflows based on conditions and actions.

**Rule Structure:**
```python
{
    "rule_id": "unique_identifier",
    "name": "Rule Name",
    "description": "Rule description",
    "conditions": [
        {"type": "node_count", "operator": "gt", "value": 5}
    ],
    "actions": [
        {"type": "add_node", "node_type": "SaveImage", "position": "end"}
    ],
    "priority": 1
}
```

#### 4. WorkflowValidator (`gimp_comfy_bridge/workflow_auto/validator.py`)
Validates workflow integrity, node compatibility, and execution requirements.

**Validation Checks:**
- Node type compatibility
- Input/output matching
- Required node presence
- Graph structure validation

#### 5. WorkflowCache (`gimp_comfy_bridge/workflow_auto/cache.py`)
Provides high-performance caching with TTL and size management.

**Features:**
- SQLite-based persistent storage
- Automatic cleanup and size management
- TTL-based expiration
- Thread-safe operations

## Configuration

Workflow settings are managed through `shared/config.py`:

```python
workflow_config = {
    "cache_db": "data/workflow_cache.db",
    "cache_ttl": 3600,  # 1 hour
    "max_cache_size": 100 * 1024 * 1024,  # 100MB
    "max_cache_entries": 1000,
    "auto_validate_workflows": True,
    "enable_rule_engine": True,
    "default_template_dir": "data/templates",
    "default_style_dir": "data/styles",
    "max_build_time": 300,  # 5 minutes
    "enable_caching": True,
    "cache_cleanup_interval": 3600,  # 1 hour
}
```

## Usage

### Basic Workflow Building

```python
from gimp_comfy_bridge.workflow_auto.builder import WorkflowBuilder

async def build_basic_workflow():
    builder = WorkflowBuilder()

    # Build workflow from template
    result = await builder.build_workflow(
        template_id="image_generation_basic",
        style_id="photorealistic",
        options={"resolution": "1024x1024", "steps": 20}
    )

    if result.success:
        workflow = result.workflow
        print(f"Built workflow with {result.node_count} nodes")
    else:
        print(f"Build failed: {result.errors}")
```

### Template Management

```python
# Get available templates
templates = await builder.get_available_templates()
for template in templates:
    print(f"Template: {template['id']} - {template['name']}")

# Get template details
details = await builder.get_template_details("image_generation_basic")
print(f"Description: {details['description']}")
```

### Rule-Based Modifications

```python
from gimp_comfy_bridge.workflow_auto.rules import RuleEngine, WorkflowRule

# Create custom rule
rule = WorkflowRule(
    rule_id="add_upsampling",
    name="Add Upsampling",
    description="Add 4x upsampling for high-res output",
    conditions=[
        {"type": "output_resolution", "operator": "lt", "value": 1024}
    ],
    actions=[
        {"type": "add_node", "node_type": "UpscaleModelLoader"},
        {"type": "add_node", "node_type": "ImageUpscaleWithModel"},
        {"type": "connect_nodes", "from": "KSampler", "to": "ImageUpscaleWithModel"}
    ],
    priority=2
)

rule_engine = RuleEngine()
rule_engine.add_rule(rule)
```

### Validation

```python
from gimp_comfy_bridge.workflow_auto.validator import WorkflowValidator

validator = WorkflowValidator()

# Validate workflow graph
result = validator.validate_graph(workflow_graph)
if not result.valid:
    print("Validation errors:")
    for error in result.errors:
        print(f"  - {error}")
```

### Caching

```python
from gimp_comfy_bridge.workflow_auto.cache import WorkflowCache

cache = WorkflowCache()

# Store workflow
await cache.store("my_workflow_key", workflow_data)

# Retrieve workflow
cached_workflow = await cache.get("my_workflow_key")

# Check cache stats
stats = await cache.get_stats()
print(f"Cache entries: {stats['entries']}, Size: {stats['size']} bytes")
```

## Web API Integration

The system integrates with the web interface through RESTful endpoints:

### Endpoints

- `GET /api/workflows/templates` - List available templates
- `GET /api/workflows/templates/{id}` - Get template details
- `POST /api/workflows/build` - Build workflow from template
- `POST /api/workflows/validate` - Validate template
- `GET /api/workflows/rules` - Get available build rules
- `POST /api/workflows/rules/apply` - Apply specific rule

### Example API Usage

```javascript
// Build workflow
const response = await fetch('/api/workflows/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        template_id: 'image_generation_advanced',
        style_id: 'anime_style',
        options: {
            resolution: '512x512',
            guidance_scale: 7.5,
            steps: 25
        }
    })
});

const result = await response.json();
if (result.success) {
    console.log('Workflow built successfully');
    // Use result.workflow for ComfyUI execution
}
```

## Template Format

Workflow templates are JSON files defining the base structure:

```json
{
    "id": "image_generation_basic",
    "name": "Basic Image Generation",
    "description": "Simple text-to-image generation workflow",
    "version": "1.0",
    "nodes": [
        {
            "id": "load_checkpoint",
            "type": "CheckpointLoaderSimple",
            "position": [100, 100],
            "inputs": {},
            "outputs": {
                "MODEL": ["CLIP", "VAE"]
            }
        }
    ],
    "connections": [
        {
            "from": "load_checkpoint",
            "from_output": "MODEL",
            "to": "ksampler",
            "to_input": "model"
        }
    ],
    "metadata": {
        "category": "generation",
        "tags": ["text-to-image", "basic"],
        "required_nodes": ["CheckpointLoaderSimple", "KSampler"]
    }
}
```

## Style Format

Styles define modifications applied to templates:

```json
{
    "id": "photorealistic",
    "name": "Photorealistic",
    "description": "High-quality photorealistic image generation",
    "modifications": [
        {
            "type": "update_node",
            "node_id": "ksampler",
            "properties": {
                "steps": 50,
                "cfg": 8.0,
                "sampler_name": "euler_ancestral"
            }
        },
        {
            "type": "add_node",
            "node_type": "ControlNetApply",
            "position": "after",
            "target_node": "load_image"
        }
    ],
    "prompt_modifiers": {
        "positive": "photorealistic, high detail, professional photography",
        "negative": "cartoon, anime, drawing, sketch"
    }
}
```

## Rule System

Rules enable intelligent workflow modifications:

### Condition Types
- `node_count`: Number of nodes in workflow
- `node_type_present`: Specific node type exists
- `output_resolution`: Output resolution requirements
- `style_applied`: Specific style has been applied
- `user_option`: User-provided option value

### Action Types
- `add_node`: Add a new node to the workflow
- `remove_node`: Remove a node from the workflow
- `update_node`: Modify node properties
- `connect_nodes`: Create connections between nodes
- `disconnect_nodes`: Remove connections between nodes
- `modify_prompt`: Update prompt text

## Performance Optimization

### Caching Strategy
- Workflows cached based on template+style+options hash
- TTL-based expiration (default 1 hour)
- Size-based cleanup (LRU eviction)
- Automatic background cleanup

### Build Optimization
- Parallel template and style loading
- Lazy rule evaluation
- Incremental validation
- Memory-efficient graph operations

## Error Handling

The system provides comprehensive error handling:

- **Template Errors**: Missing or invalid template files
- **Style Errors**: Incompatible style modifications
- **Validation Errors**: Workflow integrity issues
- **Cache Errors**: Storage and retrieval failures
- **Build Timeout**: Long-running build cancellation

## Testing

Run the test suite to validate system functionality:

```bash
python test_workflow_auto.py
```

The test suite covers:
- Component initialization
- Graph operations
- Rule evaluation
- Validation logic
- Cache operations
- Integration testing

## Future Enhancements

- **Template Marketplace**: Community template sharing
- **Advanced Rules**: Machine learning-based rule generation
- **Workflow Optimization**: Automatic performance tuning
- **Collaborative Features**: Multi-user workflow editing
- **Version Control**: Workflow versioning and rollback
- **Analytics**: Build performance and usage metrics

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Template Not Found**: Check template directory and file permissions
3. **Cache Errors**: Verify database file permissions and disk space
4. **Validation Failures**: Check node compatibility and connection requirements
5. **Build Timeouts**: Review complex templates and rule sets

### Debug Mode

Enable debug logging for detailed operation information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing to the workflow auto-generation system:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure backward compatibility
5. Test performance impact of changes

## License

This system is part of Comfy Gimpy Studio and follows the same licensing terms.