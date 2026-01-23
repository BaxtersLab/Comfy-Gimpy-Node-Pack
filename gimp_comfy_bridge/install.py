#!/usr/bin/env python3
"""
Installation script for Comfy Gimpy Node Pack GIMP Plugin.
"""

import os
import sys
import shutil
import platform
from pathlib import Path
from typing import Optional

def get_gimp_plugin_dir() -> Optional[Path]:
    """
    Get GIMP plugin directory based on platform.

    Returns:
        Optional[Path]: Plugin directory path, or None if not found.
    """
    system = platform.system()

    if system == "Windows":
        # Windows GIMP plugin directory
        appdata = os.environ.get('APPDATA')
        if appdata:
            # Try different GIMP versions
            for version in ['2.10', '2.99', '3.0']:
                plugin_dir = Path(appdata) / f'GIMP/{version}/plug-ins'
                if plugin_dir.exists():
                    return plugin_dir

    elif system == "Linux":
        # Linux GIMP plugin directory
        home = Path.home()
        # Try different GIMP versions
        for version in ['2.10', '2.99', '3.0']:
            plugin_dir = home / f'.config/GIMP/{version}/plug-ins'
            if plugin_dir.exists():
                return plugin_dir

    elif system == "Darwin":  # macOS
        # macOS GIMP plugin directory
        home = Path.home()
        # Try different GIMP versions
        for version in ['2.10', '2.99', '3.0']:
            plugin_dir = home / f'Library/Application Support/GIMP/{version}/plug-ins'
            if plugin_dir.exists():
                return plugin_dir

    return None

def find_gimp_executable() -> Optional[Path]:
    """
    Find GIMP executable in system PATH.

    Returns:
        Optional[Path]: Path to GIMP executable, or None.
    """
    system = platform.system()

    if system == "Windows":
        # Windows common locations
        common_paths = [
            Path("C:/Program Files/GIMP 2/bin/gimp-2.10.exe"),
            Path("C:/Program Files/GIMP 2/bin/gimp-console-2.10.exe"),
            Path("C:/Program Files (x86)/GIMP 2/bin/gimp-2.10.exe"),
        ]
        for path in common_paths:
            if path.exists():
                return path

    elif system == "Linux":
        # Linux common locations
        common_paths = [
            Path("/usr/bin/gimp"),
            Path("/usr/local/bin/gimp"),
            Path("/snap/bin/gimp"),
        ]
        for path in common_paths:
            if path.exists():
                return path

    elif system == "Darwin":
        # macOS common locations
        common_paths = [
            Path("/Applications/GIMP-2.10.app/Contents/MacOS/GIMP-2.10"),
            Path("/Applications/GIMP.app/Contents/MacOS/GIMP"),
        ]
        for path in common_paths:
            if path.exists():
                return path

    # Try PATH
    import shutil
    gimp_path = shutil.which("gimp")
    if gimp_path:
        return Path(gimp_path)

    return None

def install_plugin():
    """
    Install the GIMP plugin.
    """
    print("Comfy Gimpy Node Pack GIMP Plugin Installer")
    print("=" * 50)

    # Get current directory
    current_dir = Path(__file__).parent
    plugin_source = current_dir / "gimp_plugin"

    if not plugin_source.exists():
        print(f"ERROR: Plugin source directory not found: {plugin_source}")
        return False

    # Find GIMP plugin directory
    plugin_dir = get_gimp_plugin_dir()
    if not plugin_dir:
        print("ERROR: Could not find GIMP plugin directory.")
        print("Please ensure GIMP is installed and try again.")
        return False

    print(f"Found GIMP plugin directory: {plugin_dir}")

    # Create plugin directory if it doesn't exist
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Copy plugin files
    try:
        # Copy main plugin file
        main_plugin = plugin_source / "comfyui_bridge.py"
        if main_plugin.exists():
            shutil.copy2(main_plugin, plugin_dir / "comfyui_bridge.py")
            print("✓ Installed main plugin file")

        # Copy other Python files
        for py_file in plugin_source.glob("*.py"):
            if py_file.name != "comfyui_bridge.py":
                shutil.copy2(py_file, plugin_dir / py_file.name)
                print(f"✓ Installed {py_file.name}")

        # Copy any additional files (config, etc.)
        for file in plugin_source.glob("*"):
            if not file.is_dir() and file.suffix not in ['.py']:
                shutil.copy2(file, plugin_dir / file.name)
                print(f"✓ Installed {file.name}")

        print("\n✓ Plugin installation completed successfully!")
        print(f"Plugin installed to: {plugin_dir}")

        # Check for GIMP executable
        gimp_exe = find_gimp_executable()
        if gimp_exe:
            print(f"GIMP executable found: {gimp_exe}")
            print("You can restart GIMP to load the plugin.")
        else:
            print("WARNING: GIMP executable not found in PATH.")
            print("Please restart GIMP manually to load the plugin.")

        return True

    except Exception as e:
        print(f"ERROR: Failed to install plugin: {e}")
        return False

def uninstall_plugin():
    """
    Uninstall the GIMP plugin.
    """
    print("Comfy Gimpy Node Pack GIMP Plugin Uninstaller")
    print("=" * 50)

    plugin_dir = get_gimp_plugin_dir()
    if not plugin_dir:
        print("ERROR: Could not find GIMP plugin directory.")
        return False

    plugin_files = [
        "comfyui_bridge.py",
        "ui_panel.py",
        "plugin.py",
        "api_client.py",
        "utils.py",
        "config.json"
    ]

    removed = False
    for filename in plugin_files:
        plugin_file = plugin_dir / filename
        if plugin_file.exists():
            try:
                plugin_file.unlink()
                print(f"✓ Removed {filename}")
                removed = True
            except Exception as e:
                print(f"ERROR: Failed to remove {filename}: {e}")

    if removed:
        print("\n✓ Plugin uninstallation completed!")
        print("Please restart GIMP to complete the removal.")
    else:
        print("No plugin files found to remove.")

    return True

def create_config():
    """
    Create default configuration file.
    """
    current_dir = Path(__file__).parent
    config_file = current_dir / "gimp_plugin" / "config.json"

    default_config = {
        "comfyui_endpoint": "http://localhost:8188",
        "websocket_endpoint": "ws://localhost:8188/ws",
        "temp_dir": "temp",
        "default_workflow": "default",
        "auto_save": True,
        "progress_update_interval": 1.0
    }

    try:
        import json
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"✓ Created default config: {config_file}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create config: {e}")
        return False

def main():
    """
    Main installation function.
    """
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "uninstall":
            return uninstall_plugin()
        elif command == "config":
            return create_config()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python install.py [install|uninstall|config]")
            return False

    # Default to install
    return install_plugin()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)