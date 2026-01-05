#!/bin/bash

# Timestamp function for logging
ts() { date "+%Y-%m-%d %H:%M:%S"; }

echo "$(ts) [INFO] Starting inspo app wrapper..."
echo "$(ts) [INFO] Working directory: /Users/davebuckley/github/dbckz/inspo"

# Wait a moment for the display to be ready after wake
sleep 2

cd "/Users/davebuckley/github/dbckz/inspo"

# Source shell profile to get uv and other tools in PATH
if [ -f "$HOME/.zshrc" ]; then
    echo "$(ts) [INFO] Sourcing .zshrc..."
    source "$HOME/.zshrc" 2>/dev/null
fi

# Add common paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Check for --eye-break argument
if [ "$1" = "--eye-break" ]; then
    echo "$(ts) [INFO] Running uv run python inspo_app.py --eye-break..."
    exec /Users/davebuckley/.cargo/bin/uv run python inspo_app.py --eye-break 2>&1
else
    echo "$(ts) [INFO] Running uv run python inspo_app.py..."
    # Run with uv - uses PyObjC for native macOS display (no Tcl/Tk needed)
    exec /Users/davebuckley/.cargo/bin/uv run python inspo_app.py 2>&1
fi
