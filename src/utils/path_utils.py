# src/utils/path_utils.py
import os


def get_project_root():
    """
    Returns the absolute path to the project root directory.

    This should be called from anywhere in the project to get consistent paths.
    """
    # Assuming this file is in src/utils/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
