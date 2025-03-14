# src/utils/path_utils.py
import os
import sys
import datetime


def debug_print(message, also_file=True):
    """
    Print debug message to console and optionally to a debug file.

    Args:
        message (str): The message to print
        also_file (bool): Whether to also write to a debug file
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    formatted_msg = f"[{timestamp}] {message}"

    # Print to console
    print(formatted_msg)

    # Also write to file if requested
    if also_file:
        try:
            # Use user's home directory to ensure it's writable
            debug_dir = os.path.join(os.path.expanduser("~"), "ProductivityTracker_Debug")
            os.makedirs(debug_dir, exist_ok=True)

            debug_file = os.path.join(debug_dir, "debug.log")
            with open(debug_file, "a") as f:
                f.write(formatted_msg + "\n")
        except Exception as e:
            print(f"Error writing to debug file: {e}")


# Add system info logging
def log_system_info():
    """Log basic system information for debugging"""
    debug_print("=== SYSTEM INFO ===")
    debug_print(f"Python version: {sys.version}")
    debug_print(f"Platform: {sys.platform}")
    debug_print(f"Current working directory: {os.getcwd()}")
    debug_print(f"Executable path: {sys.executable}")
    debug_print(f"Sys.frozen: {getattr(sys, 'frozen', False)}")
    debug_print(f"Sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not available')}")

    # Try to create test files in different locations
    locations = [
        ("Current directory", "."),
        ("Home directory", os.path.expanduser("~")),
        ("Temp directory", os.path.join(os.path.expanduser("~"), "temp")),
        ("Executable directory", os.path.dirname(sys.executable))
    ]

    for name, path in locations:
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, "productivity_test.txt")
            with open(test_file, "w") as f:
                f.write(f"Test file created at {datetime.datetime.now()}")
            debug_print(f"Successfully wrote to {name}: {test_file}")
        except Exception as e:
            debug_print(f"Failed to write to {name}: {e}")

    debug_print("=== END SYSTEM INFO ===")


def get_project_root():
    """
    Returns the absolute path to the project root directory.

    Uses ~/ProductivityTracker when packaged, which ensures write access.
    """
    try:
        # Always use a known, writable location in the user's home directory
        # This simplifies deployment and ensures write access
        app_dir = os.path.join(os.path.expanduser("~"), "ProductivityTracker")

        # Create the directory if it doesn't exist
        os.makedirs(app_dir, exist_ok=True)

        # Also create subdirectories
        for subdir in ['data', 'logs', 'credentials', 'resources']:
            os.makedirs(os.path.join(app_dir, subdir), exist_ok=True)

        return app_dir

    except Exception as e:
        # Print error and fall back to current directory
        print(f"Error in get_project_root: {e}")
        return os.getcwd()
