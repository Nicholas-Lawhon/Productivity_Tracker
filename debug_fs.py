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


if __name__ == "__main__":
    debug_file_access()
