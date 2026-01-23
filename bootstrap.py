#!/usr/bin/env python3
"""
Bootstrap script for Comfy Gimpy Studio development environment.
Phase 10: CI/CD Infrastructure

This script sets up the local development environment with all necessary
dependencies, tools, and configurations for development and testing.
"""

import subprocess
import sys
import os
from pathlib import Path
import venv
import argparse


def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def create_virtual_environment(env_path):
    """Create a Python virtual environment."""
    print(f"Creating virtual environment at {env_path}...")
    venv.create(env_path, with_pip=True)
    print("Virtual environment created successfully.")


def install_dependencies(env_path):
    """Install project dependencies."""
    pip_path = env_path / "Scripts" / "pip" if os.name == 'nt' else env_path / "bin" / "pip"

    print("Installing main dependencies...")
    success, stdout, stderr = run_command(f'"{pip_path}" install -e .')
    if not success:
        print(f"Failed to install main dependencies: {stderr}")
        return False

    print("Installing development dependencies...")
    success, stdout, stderr = run_command(f'"{pip_path}" install -r requirements-dev.txt')
    if not success:
        print(f"Failed to install dev dependencies: {stderr}")
        return False

    print("Dependencies installed successfully.")
    return True


def setup_pre_commit():
    """Set up pre-commit hooks."""
    print("Setting up pre-commit hooks...")
    success, stdout, stderr = run_command("pre-commit install")
    if not success:
        print(f"Failed to setup pre-commit: {stderr}")
        return False

    success, stdout, stderr = run_command("pre-commit install --hook-type commit-msg")
    if not success:
        print(f"Failed to setup commit-msg hooks: {stderr}")
        return False

    print("Pre-commit hooks installed successfully.")
    return True


def run_initial_checks():
    """Run initial code quality checks."""
    print("Running initial code quality checks...")

    checks = [
        ("black --check --diff .", "Code formatting check"),
        ("isort --check-only --diff .", "Import sorting check"),
        ("ruff check .", "Linting check"),
        ("mypy .", "Type checking"),
        ("pytest --collect-only", "Test collection check")
    ]

    all_passed = True
    for command, description in checks:
        print(f"Running {description}...")
        success, stdout, stderr = run_command(command)
        if not success:
            print(f"❌ {description} failed:")
            if stderr:
                print(stderr)
            all_passed = False
        else:
            print(f"✅ {description} passed")

    return all_passed


def setup_git_hooks():
    """Set up additional git hooks if needed."""
    print("Setting up additional git hooks...")

    # Create a pre-push hook for running tests
    hooks_dir = Path(".git/hooks")
    pre_push_hook = hooks_dir / "pre-push"

    hook_content = """#!/bin/sh
# Pre-push hook to run tests before pushing
echo "Running tests before push..."
if ! python -m pytest --tb=short; then
    echo "Tests failed. Push aborted."
    exit 1
fi
echo "All tests passed. Proceeding with push."
"""

    try:
        pre_push_hook.write_text(hook_content)
        pre_push_hook.chmod(0o755)
        print("Pre-push hook created successfully.")
    except Exception as e:
        print(f"Failed to create pre-push hook: {e}")
        return False

    return True


def create_env_file():
    """Create a sample .env file for local development."""
    env_file = Path(".env.example")

    env_content = """# Comfy Gimpy Studio Development Environment Variables
# Copy this file to .env and fill in your values

# GIMP Configuration
GIMP_EXECUTABLE_PATH=C:\\Program Files\\GIMP 2\\bin\\gimp-2.10.exe
GIMP_CONFIG_DIR=%APPDATA%\\GIMP\\2.10

# ComfyUI Configuration
COMFYUI_PATH=C:\\ComfyUI
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188

# Development Settings
DEBUG=True
LOG_LEVEL=DEBUG

# Test Settings
TEST_GIMP_AVAILABLE=False
TEST_COMFYUI_AVAILABLE=False

# Marketplace Settings
MARKETPLACE_API_URL=https://api.comfy-gimpy.marketplace.com
MARKETPLACE_API_KEY=your_api_key_here
"""

    try:
        env_file.write_text(env_content)
        print(".env.example file created. Copy it to .env and configure as needed.")
    except Exception as e:
        print(f"Failed to create .env.example: {e}")
        return False

    return True


def main():
    """Main bootstrap function."""
    parser = argparse.ArgumentParser(description="Bootstrap Comfy Gimpy Studio development environment")
    parser.add_argument("--env-path", default=".venv", help="Path for virtual environment")
    parser.add_argument("--skip-checks", action="store_true", help="Skip initial code quality checks")
    parser.add_argument("--no-hooks", action="store_true", help="Skip git hooks setup")

    args = parser.parse_args()

    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    print("🚀 Bootstrapping Comfy Gimpy Studio development environment...")
    print(f"Project root: {project_root}")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version}")

    # Create virtual environment
    env_path = Path(args.env_path)
    if env_path.exists():
        print(f"Virtual environment already exists at {env_path}")
        response = input("Recreate? (y/N): ")
        if response.lower() == 'y':
            import shutil
            shutil.rmtree(env_path)
            create_virtual_environment(env_path)
    else:
        create_virtual_environment(env_path)

    # Activate virtual environment for subsequent commands
    if os.name == 'nt':
        activate_script = env_path / "Scripts" / "activate.bat"
        python_path = env_path / "Scripts" / "python.exe"
    else:
        activate_script = env_path / "bin" / "activate"
        python_path = env_path / "bin" / "python"

    # Install dependencies
    if not install_dependencies(env_path):
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Setup pre-commit
    if not setup_pre_commit():
        print("❌ Failed to setup pre-commit")
        sys.exit(1)

    # Setup additional git hooks
    if not args.no_hooks:
        if not setup_git_hooks():
            print("⚠️  Failed to setup additional git hooks")

    # Create environment file
    create_env_file()

    # Run initial checks
    if not args.skip_checks:
        print("\nRunning initial quality checks...")
        if not run_initial_checks():
            print("⚠️  Some quality checks failed. You may need to fix issues before committing.")
        else:
            print("✅ All quality checks passed!")

    print("\n🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and configure your settings")
    print("2. Activate the virtual environment:")
    if os.name == 'nt':
        print(f"   {env_path}\\Scripts\\activate.bat")
    else:
        print(f"   source {env_path}/bin/activate")
    print("3. Run tests: python -m pytest")
    print("4. Start developing!")

    if os.name == 'nt':
        print(f"\nTo activate the environment in future sessions: {env_path}\\Scripts\\activate.bat")
    else:
        print(f"\nTo activate the environment in future sessions: source {env_path}/bin/activate")


if __name__ == "__main__":
    main()