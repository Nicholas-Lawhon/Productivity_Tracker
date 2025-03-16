"""
Build script for creating Productivity Tracker executable
This script will package the application into a single executable file
using PyInstaller.
"""

import os
import shutil
import sys
import subprocess


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

    # Create directories that should exist in the packaged app
    os.makedirs(dist_dir, exist_ok=True)
    for directory in ["logs", "data", "credentials", "resources"]:
        os.makedirs(os.path.join(dist_dir, directory), exist_ok=True)

    # Create a hook file to ensure all necessary modules are included
    hook_file = os.path.join(project_root, "hook-productivity_tracker.py")
    with open(hook_file, "w") as f:
        f.write("""
# PyInstaller hook to include all necessary modules
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Include all submodules from your project
hiddenimports = collect_submodules('src')

# Add specific imports that might be missed
hiddenimports.extend([
    'sqlite3',
    'win32gui',
    'win32con',
    'win10toast',
    'gspread',
    'oauth2client',
    'oauth2client.service_account',
    'psutil'
])

# Include data files
datas = collect_data_files('src')
""")

    # Build the PyInstaller command
    pyinstaller_args = [
        "pyinstaller",
        "--name=ProductivityTracker",
        "--onefile",                 # Create a single executable
        "--windowed",                # Don't show console window
        "--clean",                   # Clean PyInstaller cache
        "--additional-hooks-dir=.",  # Add the hook file we created
        "--noconfirm",               # Don't ask for confirmation
    ]

    # Add resources directory and empty directories for logs, data, etc.
    pyinstaller_args.extend([
        "--add-data=resources;resources",
    ])

    # For debugging problems, provide a console version too
    console_debug = True
    if console_debug:
        console_args = pyinstaller_args.copy()
        console_args[1] = "--name=ProductivityTracker_Debug"
        console_args.remove("--windowed")  # Keep console window for debugging
        console_args.append("main.py")

        print("Running PyInstaller for console debug version...")
        print(" ".join(console_args))
        subprocess.run(console_args, check=True)
        print("Console debug version completed")

    # Add main.py as the script to run
    pyinstaller_args.append("main.py")

    # Run PyInstaller
    print("Running PyInstaller with the following command:")
    print(" ".join(pyinstaller_args))
    subprocess.run(pyinstaller_args, check=True)

    print("\nBuild completed! Executables created at:")
    print(f"Main application: {os.path.join(dist_dir, 'ProductivityTracker.exe')}")
    if console_debug:
        print(f"Debug version: {os.path.join(dist_dir, 'ProductivityTracker_Debug.exe')}")

    # Create a README file
    with open(os.path.join(dist_dir, "README.txt"), "w") as f:
        f.write("Productivity Tracker\n")
        f.write("===================\n\n")
        f.write("This application helps you track your productivity by timing your tasks.\n\n")
        f.write("Setup:\n")
        f.write("1. The app will create necessary folders in your home directory automatically.\n")
        f.write("2. If you want to use Google Sheets sync, place your API credentials in:\n")
        f.write("   ~/ProductivityTracker/credentials/sheets-credentials.json\n\n")
        f.write("Troubleshooting:\n")
        f.write("- If the main application has issues, try the debug version which shows detailed logs.\n")
        f.write("- Check logs in ~/ProductivityTracker/logs/ for more information.\n")


if __name__ == "__main__":
    main()