# Comfy Gimpy Studio 🎨🤖

[![CI](https://github.com/your-org/comfy-gimpy-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/comfy-gimpy-studio/actions/workflows/ci.yml)
[![Coverage](https://coveralls.io/repos/github/your-org/comfy-gimpy-studio/badge.svg)](https://coveralls.io/github/your-org/comfy-gimpy-studio)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

**Bridge the gap between GIMP and ComfyUI for seamless creative workflows**

Comfy Gimpy Studio is a powerful bridge application that connects GIMP's image editing capabilities with ComfyUI's AI-powered workflow automation, enabling creators to build sophisticated image processing pipelines with both traditional and AI-enhanced tools.

## ✨ Features

### 🎯 Core Functionality
- **Template Engine**: Dynamic template system for reusable GIMP operations
- **Style Engine**: Cascading style system for consistent visual treatments
- **Async Task Engine**: High-performance concurrent processing with priority queues
- **Workflow Automation**: Intelligent workflow orchestration and dependency management
- **Fusion Engine**: Advanced layer compositing with multiple blend modes
- **Marketplace**: Pack-based extension system for sharing templates and styles

### 🔧 Developer Experience
- **Comprehensive Testing**: Full test suite with >80% coverage
- **Type Safety**: Full type hints with mypy validation
- **Code Quality**: Automated linting, formatting, and security checks
- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment
- **Documentation**: Complete API documentation and developer guides

### 🚀 Production Ready
- **Error Handling**: Robust error handling and recovery mechanisms
- **Performance**: Optimized for large images and complex workflows
- **Security**: Secure file handling and input validation
- **Scalability**: Designed for high-throughput processing environments

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [Security](#security)
- [License](#license)

## 🚀 Installation

### Prerequisites

- **Python 3.8+**
- **GIMP 2.10+** (optional, for full GIMP integration)
- **ComfyUI** (optional, for workflow automation)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-org/comfy-gimpy-studio.git
cd comfy-gimpy-studio

# Install with pip
pip install -e .

# Or use the bootstrap script for development setup
python bootstrap.py
```

### Install from PyPI

```bash
pip install comfy-gimpy-studio
```

## 🎯 Quick Start

### Basic Usage

```python
from gimp_comfy_bridge import ComfyGimpyStudio

# Initialize the studio
studio = ComfyGimpyStudio()

# Load a template
template = studio.load_template("my_template.json")

# Apply to an image
result = studio.process_image("input.jpg", template)
result.save("output.jpg")
```

### Advanced Workflow

```python
from gimp_comfy_bridge import ComfyGimpyStudio, WorkflowBuilder

# Create a complex workflow
builder = WorkflowBuilder()
workflow = (builder
    .add_step("load_image", {"path": "input.jpg"})
    .add_step("apply_style", {"style": "vintage_film"})
    .add_step("enhance_ai", {"model": "upscale_2x"})
    .add_step("save_output", {"path": "output.jpg"})
    .build())

# Execute asynchronously
result = await studio.execute_workflow_async(workflow)
```

## 📖 Usage

### Template Engine

Create reusable templates for GIMP operations:

```python
from gimp_comfy_bridge.templates import TemplateEngine

engine = TemplateEngine()

# Create a template
template = {
    "name": "Vintage Photo",
    "operations": [
        {"type": "adjust_curves", "points": [[0, 0], [128, 100], [255, 255]]},
        {"type": "add_noise", "amount": 0.1},
        {"type": "adjust_hue", "hue": -10}
    ]
}

engine.save_template("vintage_photo.json", template)
```

### Style Engine

Define cascading styles for consistent treatments:

```python
from gimp_comfy_bridge.styles import StyleEngine

engine = StyleEngine()

# Define a style
style = {
    "name": "Cinematic",
    "properties": {
        "contrast": 1.2,
        "saturation": 0.8,
        "brightness": 1.1,
        "vignette": {"amount": 0.3, "size": 0.8}
    }
}

engine.apply_style(image, style)
```

### Async Processing

Handle large batches with the async engine:

```python
from gimp_comfy_bridge.async_engine import AsyncTaskEngine

engine = AsyncTaskEngine(max_workers=4)

# Submit multiple tasks
for image_path in image_batch:
    await engine.submit_task(
        operation="process_image",
        parameters={"path": image_path, "template": "batch_template"},
        priority=TaskPriority.NORMAL
    )

# Wait for completion
results = await engine.wait_for_all()
```

## ⚙️ Configuration

### Environment Variables

```bash
# GIMP Configuration
GIMP_EXECUTABLE_PATH=/usr/bin/gimp
GIMP_CONFIG_DIR=~/.config/GIMP/2.10

# ComfyUI Configuration
COMFYUI_PATH=/path/to/ComfyUI
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
MAX_IMAGE_SIZE=4096
```

### Configuration File

Create a `config.json`:

```json
{
  "gimp": {
    "executable_path": "/usr/bin/gimp",
    "config_dir": "~/.config/GIMP/2.10",
    "max_image_size": 4096
  },
  "comfyui": {
    "path": "/path/to/ComfyUI",
    "host": "127.0.0.1",
    "port": 8188,
    "timeout": 300
  },
  "processing": {
    "max_workers": 4,
    "queue_size": 100,
    "task_timeout": 300
  },
  "marketplace": {
    "api_url": "https://api.comfy-gimpy.marketplace.com",
    "cache_dir": "~/.cache/comfy-gimpy"
  }
}
```

## 🧪 Testing

### Run the Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_templates.py

# Run tests in verbose mode
pytest -v
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Performance Tests**: Benchmarking and profiling
- **End-to-End Tests**: Full workflow testing

## 🛠️ Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-org/comfy-gimpy-studio.git
cd comfy-gimpy-studio
python bootstrap.py

# Activate environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### Code Quality Tools

```bash
# Linting
ruff check .

# Formatting
black .

# Import sorting
isort .

# Type checking
mypy .

# Security scanning
bandit -r .
```

### Pre-commit Hooks

The project uses pre-commit hooks for automated quality checks:

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run quality checks: `pytest && ruff check . && black --check .`
5. Commit with conventional format: `git commit -m "feat: add amazing feature"`
6. Push and create a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests
- Update documentation
- Use conventional commits

## 📚 Documentation

### API Documentation

Complete API documentation is available in the `docs/` directory.

### Building Docs

```bash
# Install documentation dependencies
pip install -r requirements-dev.txt

# Build documentation
cd docs
make html
```

### User Guides

- [Getting Started Guide](docs/getting-started.md)
- [Template Creation](docs/templates.md)
- [Workflow Automation](docs/workflows.md)
- [Marketplace Guide](docs/marketplace.md)

## 🔒 Security

### Security Policy

Please see our [Security Policy](SECURITY.md) for information about reporting vulnerabilities.

### Security Best Practices

- Validate all input data
- Use secure temporary files
- Implement proper error handling
- Keep dependencies updated
- Review marketplace packs carefully

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **GIMP Team** for the powerful image editing software
- **ComfyUI Community** for the AI workflow framework
- **Contributors** for their valuable contributions
- **Open Source Community** for the tools and libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/comfy-gimpy-studio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/comfy-gimpy-studio/discussions)
- **Email**: info@comfy-gimpy.dev

---

**Made with ❤️ for the creative coding community**

[![Star History Chart](https://api.star-history.com/svg?repos=your-org/comfy-gimpy-studio&type=Date)](https://star-history.com/#your-org/comfy-gimpy-studio&Date)