#!/usr/bin/env python3
"""
Quick launcher for Protein MD TUI
Handles dependency checking and provides helpful error messages
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.11+"""
    if sys.version_info < (3, 11):
        print("❌ ERROR: Python 3.11 or higher required")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")

def check_dependency(package_name: str, import_name: str = None) -> bool:
    """Check if a Python package is installed"""
    import_name = import_name or package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_textual():
    """Install textual if missing"""
    print("\n📦 Installing Textual TUI framework...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "textual>=0.47.0"])
        print("✅ Textual installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Textual")
        print("   Try manually: pip install textual")
        return False

def main():
    """Main launcher"""
    print("=" * 60)
    print("🧬 Protein MD Simulation TUI Launcher")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Check core dependencies
    print("\n📋 Checking dependencies...")
    
    deps = {
        "textual": ("textual", "✅ Textual (TUI framework)", True),
        "autogen": ("autogen", "⚠️  AutoGen (optional, demo mode available)", False),
        "openmm": ("openmm", "⚠️  OpenMM (required for actual simulations)", False),
        "mdtraj": ("mdtraj", "ℹ️  MDTraj (optional, for analysis)", False),
    }
    
    missing_required = []
    
    for package, (import_name, desc, required) in deps.items():
        if check_dependency(package, import_name):
            print(f"  ✅ {package}")
        else:
            print(f"  ❌ {package} - {desc}")
            if required:
                missing_required.append(package)
    
    # Handle missing Textual (required)
    if "textual" in missing_required:
        print("\n⚠️  Textual is required to run the TUI")
        response = input("Install now? (y/n): ")
        if response.lower() == 'y':
            if install_textual():
                missing_required.remove("textual")
            else:
                sys.exit(1)
        else:
            print("Cannot run without Textual. Exiting.")
            sys.exit(1)
    
    # Check if protein_tui.py exists
    tui_path = Path(__file__).parent / "protein_tui.py"
    if not tui_path.exists():
        print(f"\n❌ ERROR: {tui_path} not found")
        sys.exit(1)
    
    # Show warnings for optional dependencies
    if not check_dependency("openmm"):
        print("\n⚠️  WARNING: OpenMM not installed")
        print("   TUI will run in demo mode (no actual simulations)")
        print("   Install: conda install -c conda-forge openmm")
    
    if not check_dependency("autogen"):
        print("\n⚠️  WARNING: AutoGen not installed")
        print("   TUI will run in demo mode")
        print("   Install: pip install autogen-agentchat autogen-ext")
    
    # Launch TUI
    print("\n" + "=" * 60)
    print("🚀 Launching Protein MD TUI...")
    print("   Press 'q' to quit, '?' for help")
    print("=" * 60 + "\n")
    
    import time
    time.sleep(1)
    
    # Import and run
    try:
        from protein_tui import ProteinMDTUI
        app = ProteinMDTUI()
        app.run()
    except Exception as e:
        print(f"\n❌ ERROR: Failed to launch TUI")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
