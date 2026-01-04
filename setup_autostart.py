#!/usr/bin/env python3
"""
Setup autostart for the Inspirational Quotes app.

This script configures the app to run automatically when you log in.
Uses uv for virtual environment management.
Supports Linux (with desktop environments) and macOS.
"""

import os
import sys
import stat
import shutil
import platform
import subprocess
from pathlib import Path


def get_project_path() -> Path:
    """Get the absolute path to the project directory."""
    return Path(__file__).parent.resolve()


def get_app_path() -> Path:
    """Get the absolute path to the main app."""
    return get_project_path() / "inspo_app.py"


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    return shutil.which("uv") is not None


def setup_virtualenv():
    """Create virtualenv and install dependencies using uv."""
    project_path = get_project_path()

    if not check_uv_installed():
        print("ERROR: uv is not installed!")
        print("Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)

    print("Setting up virtual environment with uv...")

    # Create venv and sync dependencies
    result = subprocess.run(
        ["uv", "sync"],
        cwd=project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error setting up virtualenv: {result.stderr}")
        sys.exit(1)

    print("Virtual environment created and dependencies installed!")
    return project_path / ".venv"


def setup_linux_autostart():
    """Setup autostart for Linux desktop environments (GNOME, KDE, XFCE, etc.)."""
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = autostart_dir / "inspo-quotes.desktop"
    project_path = get_project_path()

    # Setup virtualenv first
    setup_virtualenv()

    # Create the wrapper script that uses uv run
    wrapper_path = project_path / "run_inspo.sh"
    wrapper_content = f"""#!/bin/bash
# Wait a moment for the desktop to fully load
sleep 3

# Set display if not set
export DISPLAY="${{DISPLAY:-:0}}"

# Run the app using uv
cd "{project_path}"
uv run python inspo_app.py
"""

    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)

    # Make wrapper executable
    os.chmod(wrapper_path, os.stat(wrapper_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Inspirational Quotes
Comment=Display an inspirational quote at startup
Exec={wrapper_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
Terminal=false
"""

    with open(desktop_file, 'w') as f:
        f.write(desktop_content)

    print(f"Linux autostart configured!")
    print(f"  Desktop entry: {desktop_file}")
    print(f"  Wrapper script: {wrapper_path}")
    print("\nThe app will now run automatically when you log in.")


def setup_macos_autostart():
    """Setup autostart for macOS using LaunchAgent."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    plist_file = launch_agents_dir / "com.inspo.quotes.plist"
    project_path = get_project_path()

    # Setup virtualenv first
    setup_virtualenv()

    # Find uv path
    uv_path = shutil.which("uv")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.inspo.quotes</string>
    <key>ProgramArguments</key>
    <array>
        <string>{uv_path}</string>
        <string>run</string>
        <string>python</string>
        <string>inspo_app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{project_path}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>LaunchOnlyOnce</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/inspo-quotes.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/inspo-quotes.err</string>
</dict>
</plist>
"""

    with open(plist_file, 'w') as f:
        f.write(plist_content)

    # Load the agent
    os.system(f"launchctl load {plist_file}")

    print(f"macOS autostart configured!")
    print(f"  LaunchAgent: {plist_file}")
    print("\nThe app will now run automatically when you log in.")


def remove_linux_autostart():
    """Remove Linux autostart configuration."""
    desktop_file = Path.home() / ".config" / "autostart" / "inspo-quotes.desktop"
    wrapper_path = get_project_path() / "run_inspo.sh"

    if desktop_file.exists():
        desktop_file.unlink()
        print(f"Removed: {desktop_file}")

    if wrapper_path.exists():
        wrapper_path.unlink()
        print(f"Removed: {wrapper_path}")

    print("Linux autostart removed.")


def remove_macos_autostart():
    """Remove macOS autostart configuration."""
    plist_file = Path.home() / "Library" / "LaunchAgents" / "com.inspo.quotes.plist"

    if plist_file.exists():
        os.system(f"launchctl unload {plist_file}")
        plist_file.unlink()
        print(f"Removed: {plist_file}")

    print("macOS autostart removed.")


def main():
    """Main entry point."""
    system = platform.system()

    print("=" * 60)
    print("Inspirational Quotes - Autostart Setup (using uv)")
    print("=" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        print("Removing autostart configuration...")
        if system == "Linux":
            remove_linux_autostart()
        elif system == "Darwin":
            remove_macos_autostart()
        else:
            print(f"Unsupported platform: {system}")
        return

    # Check for uv
    if not check_uv_installed():
        print("ERROR: uv is not installed!")
        print()
        print("Install uv with:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print()
        sys.exit(1)

    print(f"Detected platform: {system}")
    print()

    if system == "Linux":
        setup_linux_autostart()
    elif system == "Darwin":
        setup_macos_autostart()
    else:
        print(f"Unsupported platform: {system}")
        print("Supported platforms: Linux, macOS")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Setup complete! Test the app by running:")
    print(f"  cd {get_project_path()}")
    print("  uv run python inspo_app.py")
    print()
    print("To remove autostart, run:")
    print(f"  python {__file__} --remove")
    print("=" * 60)


if __name__ == "__main__":
    main()
