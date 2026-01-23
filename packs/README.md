# Comfy Gimpy Studio Marketplace Pack System

The Marketplace Pack System enables creation, distribution, and management of reusable content packs for Comfy Gimpy Studio. This system supports template packs, style packs, workflow packs, and model packs with full metadata, versioning, dependencies, and licensing support.

## Features

- **Pack Types**: Support for template, style, workflow, and model packs
- **Metadata Management**: Comprehensive pack metadata with previews, descriptions, and tags
- **Versioning**: Semantic versioning with dependency management
- **Validation**: Automatic pack structure and content validation
- **Registry**: SQLite-based pack registry with search and indexing
- **Installation**: Safe pack installation with backup and rollback support
- **Web API**: RESTful API for web interface integration
- **Export Formats**: ZIP and directory export formats

## Pack Structure

Each pack contains a `manifest.json` file with the following structure:

```json
{
  "id": "unique-pack-id",
  "type": "template|style|workflow|model",
  "name": "Pack Display Name",
  "version": "1.0.0",
  "created_at": "2024-01-01T00:00:00Z",
  "content": {
    // Pack-specific content
  },
  "metadata": {
    // Additional metadata
  },
  "previews": [
    {
      "filename": "preview1.png",
      "path": "previews/preview1.png",
      "checksum": "md5-hash",
      "size": 12345
    }
  ],
  "dependencies": [
    {
      "name": "other-pack",
      "version": ">=1.0.0",
      "type": "template",
      "required": true
    }
  ],
  "license": "MIT",
  "author": "Pack Author",
  "description": "Pack description",
  "tags": ["tag1", "tag2"]
}
```

## Usage

### Creating Packs

```python
from packs.packager import Packager
from shared.config import Config

config = Config()
packager = Packager(config)

# Create a template pack
result = await packager.create_pack(
    pack_type="template",
    name="My Template Pack",
    version="1.0.0",
    description="A collection of useful templates",
    author="Your Name",
    license="MIT",
    tags=["templates", "useful"],
    content={
        "templates": [
            {"name": "template1", "data": "..."},
            {"name": "template2", "data": "..."}
        ]
    },
    metadata={"category": "general"},
    dependencies=[],
    previews=[]
)

print(f"Pack created: {result['pack_id']}")
```

### Validating Packs

```python
from packs.validator import PackValidator

validator = PackValidator(config)

# Validate a pack file
is_valid, errors, manifest = await validator.validate_pack("/path/to/pack.zip")

if is_valid:
    print("Pack is valid!")
else:
    print(f"Validation errors: {errors}")
```

### Managing Pack Registry

```python
from packs.registry import PackRegistry

registry = PackRegistry(config)

# List all packs
packs = registry.list_packs(pack_type="template", limit=10)

# Search packs
results = registry.search_packs("useful templates", pack_type="template")

# Get pack info
pack_info = registry.get_pack("pack-id")
```

### Installing Packs

```python
from packs.installer import PackInstaller
from packs.registry import PackRegistry

registry = PackRegistry(config)
installer = PackInstaller(config, registry)

# Install a pack
result = await installer.install_pack("/path/to/pack.zip")

if result.success:
    print(f"Pack installed: {result.pack_id}")
else:
    print(f"Installation failed: {result.error}")

# Update a pack
update_result = await installer.update_pack("pack-id", "/path/to/new-pack.zip")

# Uninstall a pack
success = await installer.uninstall_pack("pack-id")
```

## Web API

The pack system provides a RESTful API for web interface integration:

### Endpoints

- `POST /api/packs/create` - Create a new pack
- `GET /api/packs/export/{pack_id}` - Export a pack
- `POST /api/packs/validate` - Validate a pack file
- `POST /api/packs/install` - Install a pack
- `POST /api/packs/update/{pack_id}` - Update a pack
- `DELETE /api/packs/uninstall/{pack_id}` - Uninstall a pack
- `GET /api/packs/` - List packs
- `GET /api/packs/{pack_id}` - Get pack details
- `GET /api/packs/search` - Search packs
- `GET /api/packs/types` - Get pack types
- `GET /api/packs/stats` - Get pack statistics

### Example API Usage

```javascript
// Create a pack
const formData = new FormData();
formData.append('pack_type', 'template');
formData.append('name', 'My Pack');
formData.append('version', '1.0.0');
// ... other fields

const response = await fetch('/api/packs/create', {
    method: 'POST',
    body: formData
});
const result = await response.json();

// Install a pack
const installResponse = await fetch('/api/packs/install', {
    method: 'POST',
    body: packFile
});
const installResult = await installResponse.json();
```

## Configuration

Pack system configuration is managed through `shared/config.py`:

```python
config = Config()

# Pack-specific settings
config.set_pack_config('default_license', 'MIT')
config.set_pack_config('max_pack_size', 100 * 1024 * 1024)  # 100MB
config.set_pack_config('auto_validate', True)
config.set_pack_config('backup_on_update', True)
```

## Directory Structure

```
data/
├── packs/
│   ├── installed/     # Installed packs
│   ├── backups/       # Pack backups
│   ├── temp/         # Temporary files
│   └── packs.db      # Pack registry database
├── exports/          # Exported packs
└── config.json      # User configuration
```

## Dependencies

- Python 3.8+
- aiofiles
- sqlite3 (built-in)
- hashlib (built-in)
- json (built-in)
- zipfile (built-in)
- pathlib (built-in)

## Error Handling

The pack system provides comprehensive error handling:

- **Validation Errors**: Detailed validation messages for pack structure issues
- **Dependency Errors**: Clear dependency resolution failure messages
- **Installation Errors**: Safe rollback on installation failures
- **Registry Errors**: Database integrity and constraint violation handling

## Security

- **Checksum Validation**: MD5 checksums for pack integrity verification
- **Path Sanitization**: Safe path handling to prevent directory traversal
- **Size Limits**: Configurable maximum pack sizes
- **Permission Checks**: File system permission validation

## Future Enhancements

- Pack sharing and collaboration features
- Marketplace discovery and download
- Pack analytics and usage tracking
- Advanced dependency resolution
- Pack conflict detection and resolution
- Cloud storage integration
- Pack signing and verification