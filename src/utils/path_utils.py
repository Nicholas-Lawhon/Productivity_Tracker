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
    In development: Uses the actual project directory
    When packaged: Uses ~/ProductivityTracker
    """
    try:
        # Check if we're running in the development environment
        # by looking for common project structure indicators
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Go up one level (from src/utils to src)
        parent_dir = os.path.dirname(current_dir)

        # Go up one more level (from src to project root)
        potential_project_root = os.path.dirname(parent_dir)

        # Check if we're in development environment by looking for common files/directories
        dev_indicators = [
            os.path.isdir(os.path.join(potential_project_root, 'src')),
            os.path.isdir(os.path.join(potential_project_root, '.git')),
            os.path.isdir(os.path.join(potential_project_root, '.idea')),
            os.path.isfile(os.path.join(potential_project_root, 'main.py')),
            os.path.isfile(os.path.join(potential_project_root, 'Requirements.txt'))
        ]

        # If at least 2 development indicators are found, we're likely in dev mode
        if sum(dev_indicators) >= 2:
            print(f"Development environment detected, using project directory: {potential_project_root}")

            # Ensure the required directories exist
            for subdir in ['data', 'logs', 'credentials', 'resources']:
                os.makedirs(os.path.join(potential_project_root, subdir), exist_ok=True)

            return potential_project_root

        # If we're not in development, use the home directory approach for packaged app
        app_dir = os.path.join(os.path.expanduser("~"), "ProductivityTracker")
        print(f"Using application directory in home folder: {app_dir}")

        # Create the directory and subdirectories if they don't exist
        os.makedirs(app_dir, exist_ok=True)
        for subdir in ['data', 'logs', 'credentials', 'resources']:
            os.makedirs(os.path.join(app_dir, subdir), exist_ok=True)

        return app_dir

    except Exception as e:
        # Print error and fall back to current directory
        print(f"Error in get_project_root: {e}")
        import traceback
        print(traceback.format_exc())
        return os.getcwd()


def debug_app_paths():
    """
    Debug function to verify all application paths and write access.
    Call this early in your application startup to diagnose path issues.
    """
    project_root = get_project_root()
    print(f"\n=== DEBUG APP PATHS ===")
    print(f"Project root: {project_root}")

    # Check Python executable and working directory
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")

    # Test critical directories
    paths_to_check = {
        'logs_dir': os.path.join(project_root, 'logs'),
        'data_dir': os.path.join(project_root, 'data'),
        'db_file': os.path.join(project_root, 'data', 'local_db.sqlite'),
        'credentials_dir': os.path.join(project_root, 'credentials'),
        'resources_dir': os.path.join(project_root, 'resources')
    }

    for name, path in paths_to_check.items():
        print(f"\nChecking {name}: {path}")

        # For directories
        if name.endswith('_dir'):
            if not os.path.exists(path):
                print(f"  Directory doesn't exist. Creating...")
                try:
                    os.makedirs(path, exist_ok=True)
                    print(f"  Created directory successfully.")
                except Exception as e:
                    print(f"  ERROR creating directory: {e}")
                    continue

            # Test write access to directory
            test_file = os.path.join(path, "write_test.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("Test write")
                print(f"  Successfully wrote to test file: {test_file}")
                os.remove(test_file)
                print(f"  Successfully removed test file")
            except Exception as e:
                print(f"  ERROR: Cannot write to directory: {e}")

        # For the database file
        elif name == 'db_file':
            db_dir = os.path.dirname(path)

            # Make sure db directory exists
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    print(f"  Created database directory: {db_dir}")
                except Exception as e:
                    print(f"  ERROR creating database directory: {e}")
                    continue

            # Check if db file exists and we can connect to it
            if os.path.exists(path):
                print(f"  Database file exists")
                try:
                    import sqlite3
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    print(f"  Database integrity check: {result}")
                    conn.close()
                except Exception as e:
                    print(f"  ERROR accessing existing database: {e}")
            else:
                print(f"  Database file doesn't exist yet")
                try:
                    # Try to create a simple test table
                    import sqlite3
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
                    conn.commit()
                    conn.close()
                    print(f"  Successfully created and accessed test database")
                except Exception as e:
                    print(f"  ERROR creating test database: {e}")

    print("\n=== END DEBUG APP PATHS ===\n")
