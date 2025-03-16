# Save as debug_fs.py in your project root
import os
import sys
import tempfile


def debug_file_access():
    """Test basic file system access."""
    print(f"Current working directory: {os.getcwd()}")
    print(f"Executable path: {sys.executable}")

    # Test writing to current directory
    try:
        with open("test_cwd.txt", "w") as f:
            f.write("Test file in current directory")
        print("Successfully wrote to current directory")
    except Exception as e:
        print(f"Failed to write to current directory: {e}")

    # Test writing to temp directory
    try:
        temp_path = os.path.join(tempfile.gettempdir(), "productivity_test.txt")
        with open(temp_path, "w") as f:
            f.write("Test file in temp directory")
        print(f"Successfully wrote to temp directory: {temp_path}")
    except Exception as e:
        print(f"Failed to write to temp directory: {e}")

    # Test with absolute path
    app_data = os.path.expanduser("~/ProductivityTracker")
    os.makedirs(app_data, exist_ok=True)
    try:
        test_path = os.path.join(app_data, "test.txt")
        with open(test_path, "w") as f:
            f.write("Test file in app data")
        print(f"Successfully wrote to app data: {test_path}")
    except Exception as e:
        print(f"Failed to write to app data: {e}")


def check_app_paths():
    from src.utils.path_utils import get_project_root

    project_root = get_project_root()
    print(f"Project root: {project_root}")

    paths_to_check = [
        os.path.join(project_root, 'logs'),
        os.path.join(project_root, 'data'),
        os.path.join(project_root, 'data', 'local_db.sqlite'),
        os.path.join(project_root, 'credentials')
    ]

    for path in paths_to_check:
        print(f"Checking path: {path}")
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False
        writable = os.access(path, os.W_OK) if exists else False
        print(f"  Exists: {exists}, Is Directory: {is_dir}, Writable: {writable}")

        # Try creating a test file if it's a directory
        if is_dir:
            test_file = os.path.join(path, "test_write.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("Test write")
                print(f"  Successfully wrote to {test_file}")
                os.remove(test_file)
            except Exception as e:
                print(f"  Failed to write to {test_file}: {e}")


if __name__ == "__main__":
    debug_file_access()
