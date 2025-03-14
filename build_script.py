"""
Build script for creating Productivity Tracker executable
This script will package the application into a single executable file
using PyInstaller.
"""

import os
import shutil
import sys
import subprocess
import platform
from pathlib import Path


def main():
    # Ensure we're in the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print(f"Building from project root: {project_root}")

    # Create build directory if it doesn't exist
    build_dir = os.path.join(project_root, "build")
    dist_dir = os.path.join(project_root, "dist")

    # Clean previous build files if they exist
    print("Cleaning previous build files...")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)

    # Make sure PyInstaller is installed
    try:
        print("Checking for PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("PyInstaller is installed.")
    except subprocess.CalledProcessError:
        print("Failed to install PyInstaller. Please install it manually with:")
        print("pip install pyinstaller")
        return

    # Prepare directories to include
    data_dirs = [
        os.path.join(project_root, "resources"),
    ]

    # Create directories that should exist in the packaged app
    for directory in ["logs", "data", "credentials"]:
        os.makedirs(os.path.join(dist_dir, directory), exist_ok=True)

    # Build the PyInstaller command
    pyinstaller_args = [
        "pyinstaller",
        "--name=ProductivityTracker",
        "--onefile",  # Create a single executable
        "--windowed",  # Don't show console window
        "--clean",  # Clean PyInstaller cache
        f"--icon={os.path.join('resources', 'desktop_shortcut_icon.ico')}",  # App icon
        "--add-data=resources;resources",  # Include resources directory
    ]

    # Add main.py as the script to run
    pyinstaller_args.append("main.py")

    # Run PyInstaller
    print("Running PyInstaller with the following command:")
    print(" ".join(pyinstaller_args))
    subprocess.run(pyinstaller_args, check=True)

    print("\nBuild completed! Executable created at:")
    print(f"{os.path.join(dist_dir, 'ProductivityTracker.exe')}")

    # Create a README file in the dist directory
    with open(os.path.join(dist_dir, "README.txt"), "w") as f:
        f.write("Productivity Tracker\n")
        f.write("===================\n\n")
        f.write("This application helps you track your productivity by timing your tasks.\n\n")
        f.write("Setup:\n")
        f.write("1. Create a 'credentials' folder if you want to use Google Sheets sync\n")
        f.write("2. Place your Google Sheets API credentials in the 'credentials' folder\n")
        f.write("3. Run ProductivityTracker.exe\n\n")
        f.write("The application will create necessary folders for logs and data automatically.\n")

    print("\nAdditional files have been created in the dist directory.")
    print("You can distribute the entire 'dist' folder to users.")


if __name__ == "__main__":
    main()
