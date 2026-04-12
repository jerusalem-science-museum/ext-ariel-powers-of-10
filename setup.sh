#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "=== Kiosk App Setup ==="
echo "Project directory: $SCRIPT_DIR"
echo "(Run kiosk-base-setup.sh first on a fresh machine if you haven't already.)"
echo "https://raw.githubusercontent.com/wiki/jerusalem-science-museum/.github/kiosk-base-setup.sh"
echo ""
# =========================================================================
# 1. Python venv & dependencies
# =========================================================================
echo ""
echo "=== Setting up Python environment ==="
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
else
    echo "  ✓ Existing .venv found — skipping creation"
fi

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    "$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    echo "  ✓ Dependencies installed from requirements.txt"
else
    echo "  ⚠️  No requirements.txt found — skipping pip install"
fi

echo "  ✓ Venv ready at $SCRIPT_DIR/.venv"
# =========================================================================
# 2. Make scripts executable
# =========================================================================
chmod +x "$SCRIPT_DIR/run.sh"

# =========================================================================
# 3. Autostart: app
# =========================================================================
echo ""
echo "=== Setting up app autostart ==="
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/app.desktop << EOF
[Desktop Entry]
Type=Application
Name=My Exhibition App
Exec=bash $SCRIPT_DIR/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# =========================================================================
# Done
# =========================================================================
echo ""
echo "========================================="
echo "  App setup complete! Reboot to apply."
echo "========================================="
echo ""
echo "What was done:"
echo "  [Python]       Created .venv and installed requiremnets"
echo "  [App]          Will auto-launch via run.sh on login"
echo ""
echo "Rebooting now is recommended: sudo reboot"
