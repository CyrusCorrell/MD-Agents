#!/bin/bash
# Unix/Linux/Mac launcher for Protein MD TUI

echo "============================================================"
echo "🧬 Protein MD Simulation TUI Launcher"
echo "============================================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 not found"
    echo "   Please install Python 3.11+ from python.org"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Launch the Python launcher
python3 launch_tui.py

# Check exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ TUI exited with error"
    read -p "Press enter to continue..."
fi
