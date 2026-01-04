#!/usr/bin/env python3
"""
Setup autostart for the Inspirational Quotes app.

This script configures the app to run automatically when:
- You log in
- Your laptop wakes from sleep/suspend

Uses uv for virtual environment management.
Supports Linux (with systemd) and macOS.
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


def get_uv_path() -> str:
    """Get the full path to uv."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    # Common locations if not in PATH
    for path in ["~/.cargo/bin/uv", "~/.local/bin/uv", "/usr/local/bin/uv"]:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return expanded
    return "uv"


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
    """Setup autostart for Linux - both login and wake from suspend."""
    project_path = get_project_path()
    uv_path = get_uv_path()

    # Setup virtualenv first
    setup_virtualenv()

    # Create the wrapper script that uses uv run
    wrapper_path = project_path / "run_inspo.sh"
    wrapper_content = f"""#!/bin/bash
# Wrapper script to run the inspirational quotes app

# Wait a moment for the desktop/display to be ready
sleep 2

# Try to find the display
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Get the current user's DBUS session
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

# Run the app using uv
cd "{project_path}"
{uv_path} run python inspo_app.py
"""

    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    os.chmod(wrapper_path, os.stat(wrapper_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # 1. Setup desktop autostart for login
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = autostart_dir / "inspo-quotes.desktop"
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

    print(f"Login autostart configured: {desktop_file}")

    # 2. Setup systemd user service for wake from suspend
    systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    # Create the service file
    service_file = systemd_user_dir / "inspo-quotes.service"
    service_content = f"""[Unit]
Description=Inspirational Quotes Display
After=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart={wrapper_path}
Environment=DISPLAY=:0

[Install]
WantedBy=suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
"""

    with open(service_file, 'w') as f:
        f.write(service_content)

    print(f"Systemd service created: {service_file}")

    # Enable the service
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    result = subprocess.run(
        ["systemctl", "--user", "enable", "inspo-quotes.service"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("Systemd service enabled for wake-from-sleep!")
    else:
        print(f"Note: Could not enable systemd service: {result.stderr}")
        print("The app will still run on login, but may not run on wake from sleep.")

    print()
    print("Linux setup complete!")
    print("  - Will run on login (desktop autostart)")
    print("  - Will run on wake from sleep (systemd service)")


def compile_unlock_watcher(project_path: Path) -> Path:
    """Compile the Swift unlock watcher binary."""
    swift_source = project_path / "unlock_watcher.swift"
    binary_path = project_path / "unlock_watcher"

    if not swift_source.exists():
        print(f"Warning: {swift_source} not found, skipping unlock watcher")
        return None

    print("Compiling unlock watcher...")
    result = subprocess.run(
        ["swiftc", "-o", str(binary_path), str(swift_source)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Warning: Failed to compile unlock watcher: {result.stderr}")
        return None

    os.chmod(binary_path, os.stat(binary_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Unlock watcher compiled: {binary_path}")
    return binary_path


def setup_macos_autostart():
    """Setup autostart for macOS - login, wake from sleep, and screen unlock."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    project_path = get_project_path()
    uv_path = get_uv_path()

    # Setup virtualenv first
    setup_virtualenv()

    # Create a wrapper script that handles wake detection
    wrapper_path = project_path / "run_inspo.sh"
    wrapper_content = f"""#!/bin/bash
# Wait a moment for the display to be ready after wake
sleep 2

# Run the app using uv
cd "{project_path}"
{uv_path} run python inspo_app.py
"""

    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    os.chmod(wrapper_path, os.stat(wrapper_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # 1. LaunchAgent for login
    plist_file = launch_agents_dir / "com.inspo.quotes.plist"
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.inspo.quotes</string>
    <key>ProgramArguments</key>
    <array>
        <string>{wrapper_path}</string>
    </array>
    <key>RunAtLoad</key>
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

    # Load the login agent
    os.system(f"launchctl unload {plist_file} 2>/dev/null")
    os.system(f"launchctl load {plist_file}")

    print(f"Login autostart configured: {plist_file}")

    # 2. Compile and setup unlock watcher (for Touch ID and screen unlock)
    unlock_binary = compile_unlock_watcher(project_path)

    if unlock_binary:
        unlock_plist_file = launch_agents_dir / "com.inspo.unlockwatcher.plist"
        unlock_plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.inspo.unlockwatcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>{unlock_binary}</string>
        <string>{wrapper_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/inspo-unlock-watcher.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/inspo-unlock-watcher.err</string>
</dict>
</plist>
"""
        with open(unlock_plist_file, 'w') as f:
            f.write(unlock_plist_content)

        os.system(f"launchctl unload {unlock_plist_file} 2>/dev/null")
        os.system(f"launchctl load {unlock_plist_file}")

        print(f"Screen unlock watcher configured: {unlock_plist_file}")
        print()
        print("macOS setup complete!")
        print("  - Will run on login")
        print("  - Will run on screen unlock (Touch ID, password, etc.)")
        print("  - Will run on wake from sleep")
        print()
        print("Note: There's a 60-second cooldown between triggers to prevent duplicates.")
    else:
        print()
        print("macOS login autostart configured!")
        print()
        print("Note: Screen unlock detection requires Swift compiler (Xcode).")
        print("Install Xcode Command Line Tools: xcode-select --install")
        print("Then run this setup script again.")
        print()
        print("Currently configured:")
        print("  - Will run on login")
        print("  - Will NOT run on screen unlock (Swift compiler not available)")


def remove_linux_autostart():
    """Remove Linux autostart configuration."""
    desktop_file = Path.home() / ".config" / "autostart" / "inspo-quotes.desktop"
    service_file = Path.home() / ".config" / "systemd" / "user" / "inspo-quotes.service"
    wrapper_path = get_project_path() / "run_inspo.sh"

    # Disable and remove systemd service
    subprocess.run(
        ["systemctl", "--user", "disable", "inspo-quotes.service"],
        capture_output=True
    )

    if service_file.exists():
        service_file.unlink()
        print(f"Removed: {service_file}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

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
    unlock_plist_file = Path.home() / "Library" / "LaunchAgents" / "com.inspo.unlockwatcher.plist"
    wrapper_path = get_project_path() / "run_inspo.sh"
    unlock_binary = get_project_path() / "unlock_watcher"

    if plist_file.exists():
        os.system(f"launchctl unload {plist_file} 2>/dev/null")
        plist_file.unlink()
        print(f"Removed: {plist_file}")

    if unlock_plist_file.exists():
        os.system(f"launchctl unload {unlock_plist_file} 2>/dev/null")
        unlock_plist_file.unlink()
        print(f"Removed: {unlock_plist_file}")

    if wrapper_path.exists():
        wrapper_path.unlink()
        print(f"Removed: {wrapper_path}")

    if unlock_binary.exists():
        unlock_binary.unlink()
        print(f"Removed: {unlock_binary}")

    print("macOS autostart removed.")


def main():
    """Main entry point."""
    system = platform.system()

    print("=" * 60)
    print("Inspirational Quotes - Autostart Setup (using uv)")
    print("=" * 60)
    print()
    print("This will configure the app to run:")
    print("  1. When you log in")
    print("  2. When your laptop wakes from sleep")
    print("  3. When you unlock your screen (macOS: Touch ID, password, etc.)")
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
