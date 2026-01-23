# Contributing to Comfy Gimpy Studio

Thank you for your interest in contributing to Comfy Gimpy Studio! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- GIMP 2.10 or higher (optional, for full functionality)
- ComfyUI (optional, for workflow testing)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/comfy-gimpy-studio.git
   cd comfy-gimpy-studio
   ```

2. **Run the bootstrap script**
   ```bash
   python bootstrap.py
   ```

   This will:
   - Create a virtual environment
   - Install all dependencies
   - Set up pre-commit hooks
   - Run initial quality checks

3. **Activate the virtual environment**
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

## Development Workflow

### 1. Choose an Issue

- Check the [issue tracker](https://github.com/your-org/comfy-gimpy-studio/issues) for open issues
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write clear, concise commit messages
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 4. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Run all tests
pytest

# Run linting
ruff check .

# Check formatting
black --check .
isort --check-only .

# Type checking
mypy .
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `style:` for formatting
- `refactor:` for code restructuring
- `test:` for test additions
- `chore:` for maintenance

### 6. Push and Create Pull Request

```bash
git push origin your-branch-name
```

Then create a pull request on GitHub with:
- Clear description of changes
- Reference to related issues
- Screenshots/videos for UI changes

## Code Quality Standards

### Python Style

- Follow PEP 8
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters (Black default)
- Use descriptive variable and function names

### Testing

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Mock external dependencies (GIMP, ComfyUI, file I/O)

### Documentation

- Add docstrings to all public functions/classes
- Update README.md for user-facing changes
- Update this CONTRIBUTING.md for process changes

## Project Structure

```
comfy-gimpy-studio/
├── gimp_comfy_bridge/          # Main package
│   ├── __init__.py
│   ├── templates.py            # Template engine
│   ├── styles.py               # Style engine
│   ├── async_engine.py         # Async task engine
│   ├── workflow_auto.py        # Workflow automation
│   ├── fusion_engine.py        # Image fusion engine
│   └── packs.py                # Marketplace packaging
├── shared/                     # Shared utilities
│   ├── types.py
│   └── utils.py
├── tests/                      # Test suite
├── docs/                       # Documentation
├── .github/workflows/          # CI/CD pipelines
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md
```

## Testing Guidelines

### Unit Tests

- Place tests in `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test class and method names
- Follow AAA pattern: Arrange, Act, Assert

### Integration Tests

- Test component interactions
- Mock external services
- Use fixtures for complex setup

### Test Coverage

- Run `pytest --cov=.` to check coverage
- Aim for >80% coverage on new code
- Cover both success and error paths

## Pull Request Process

1. **Ensure CI passes** - All GitHub Actions checks must pass
2. **Get reviews** - At least one maintainer review required
3. **Address feedback** - Make requested changes or explain why not
4. **Merge** - Maintainers will merge approved PRs

## Commit Message Guidelines

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

Examples:
```
feat(templates): add support for nested template variables

fix(async): resolve race condition in task queue

docs(readme): update installation instructions
```

## Issue Reporting

When reporting bugs or requesting features:

1. **Check existing issues** - Search before creating new issues
2. **Use issue templates** - Fill out all required fields
3. **Provide details** - Include steps to reproduce, expected vs actual behavior
4. **Add labels** - Help categorize the issue

## Getting Help

- **Documentation**: Check the `docs/` directory
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Create issues for bugs/features
- **Discord/Slack**: Join our community chat

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

Contributors are recognized in:
- GitHub's contributor insights
- Release notes
- Special mentions in documentation

Thank you for contributing to Comfy Gimpy Studio! 🎨🤖