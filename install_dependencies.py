#!/usr/bin/env python3
"""
Dependency installer for Age of Mythology Retold Modding Tools

This script helps install required dependencies in Blender's Python environment.
Run this script from Blender's Python console or as a standalone script.

Usage in Blender:
1. Open Blender's Python console (Window > Toggle System Console)
2. Copy and paste this script
3. Run it to install dependencies

Usage as standalone:
python install_dependencies.py [blender_python_path]
"""

import sys
import subprocess
import os
from pathlib import Path


def find_blender_python():
    """Try to find Blender's Python executable automatically."""
    possible_paths = []
    
    # Windows paths
    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        for version in ["4.0", "3.6", "3.5", "3.4", "3.3"]:
            path = (Path(program_files) / "Blender Foundation" / 
                   f"Blender {version}" / version / "python" / "bin" / "python.exe")
            if path.exists():
                possible_paths.append(str(path))
    
    # macOS paths
    elif sys.platform == "darwin":
        for version in ["4.0", "3.6", "3.5", "3.4", "3.3"]:
            path = (Path("/Applications/Blender.app/Contents/Resources") / 
                   version / "python" / "bin" / "python3")
            if path.exists():
                possible_paths.append(str(path))
    
    # Linux paths
    elif sys.platform.startswith("linux"):
        for version in ["4.0", "3.6", "3.5", "3.4", "3.3"]:
            path = Path(f"/usr/share/blender/{version}/python/bin/python3")
            if path.exists():
                possible_paths.append(str(path))
    
    return possible_paths


def install_dependencies(python_path):
    """Install dependencies using the specified Python executable."""
    try:
        # Check if numpy is already installed
        result = subprocess.run(
            [python_path, "-c", "import numpy; print('numpy version:', numpy.__version__)"], 
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f" numpy is already installed: {result.stdout.strip()}")
            return True
        
        # Install numpy
        print(f"Installing numpy using {python_path}...")
        result = subprocess.run([python_path, "-m", "pip", "install", "numpy>=1.21.0"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(" numpy installed successfully!")
            return True
        else:
            print(f" Failed to install numpy:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f" Error installing dependencies: {e}")
        return False


def main():
    """Main function to handle dependency installation."""
    print("Age of Mythology Retold Modding Tools - Dependency Installer")
    print("=" * 60)
    
    # Check if we're running in Blender
    try:
        import bpy
        print(" Running in Blender environment")
        blender_python = sys.executable
        print(f"Using Blender's Python: {blender_python}")
        
        # Install dependencies
        if install_dependencies(blender_python):
            print("\n All dependencies installed successfully!")
            print("You can now install the addon in Blender.")
        else:
            print("\n Failed to install dependencies.")
            print("Please try installing manually using the instructions in README.md")
        
    except ImportError:
        print("Running outside Blender environment")
        
        # Check command line arguments
        if len(sys.argv) > 1:
            blender_python = sys.argv[1]
            print(f"Using specified Python path: {blender_python}")
        else:
            # Try to find Blender Python automatically
            possible_paths = find_blender_python()
            
            if not possible_paths:
                print(" Could not find Blender Python automatically.")
                print("Please provide the path to Blender's Python executable:")
                print("python install_dependencies.py [blender_python_path]")
                print("\nCommon paths:")
                print("- Windows: C:\\Program Files\\Blender Foundation\\Blender 4.0\\4.0\\python\\bin\\python.exe")
                print("- macOS: /Applications/Blender.app/Contents/Resources/4.0/python/bin/python3")
                print("- Linux: /usr/share/blender/4.0/python/bin/python3")
                return
            
            blender_python = possible_paths[0]
            print(f"Found Blender Python: {blender_python}")
        
        # Install dependencies
        if install_dependencies(blender_python):
            print("\n All dependencies installed successfully!")
            print("You can now install the addon in Blender.")
        else:
            print("\n Failed to install dependencies.")
            print("Please try installing manually using the instructions in README.md")


if __name__ == "__main__":
    main() 