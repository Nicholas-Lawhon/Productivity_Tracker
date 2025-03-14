import sys
import traceback
from PyQt5 import QtWidgets
from src.ui.main_window import MainWindow
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os
import datetime

# Setup basic error handling and logging before anything else
try:
    # Create debug log in user's home directory
    debug_dir = os.path.join(os.path.expanduser("~"), "ProductivityTracker_Debug")
    os.makedirs(debug_dir, exist_ok=True)
    debug_file = os.path.join(debug_dir, "startup_debug.log")


    def direct_log(message):
        """Write directly to the debug log file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(debug_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")


    direct_log("=== APPLICATION STARTING ===")
    direct_log(f"Python version: {sys.version}")
    direct_log(f"Platform: {sys.platform}")
    direct_log(f"Executable: {sys.executable}")
    direct_log(f"CWD: {os.getcwd()}")
    direct_log(f"Frozen: {getattr(sys, 'frozen', False)}")


    # Add a global exception hook
    def global_exception_hook(exctype, value, tb):
        """Global exception handler to log all unhandled exceptions"""
        error_msg = "".join(traceback.format_exception(exctype, value, tb))
        direct_log(f"UNHANDLED EXCEPTION: {error_msg}")
        sys.__excepthook__(exctype, value, tb)


    sys.excepthook = global_exception_hook
    direct_log("Global exception hook installed")

    # Create and ensure necessary directories exist
    app_dir = get_project_root()
    direct_log(f"Project root: {app_dir}")

    for directory in ['data', 'logs', 'credentials', 'resources']:
        dir_path = os.path.join(app_dir, directory)
        os.makedirs(dir_path, exist_ok=True)
        direct_log(f"Initialized directory: {dir_path}")

        # Try to write a test file
        try:
            test_file = os.path.join(dir_path, "test_file.txt")
            with open(test_file, "w") as f:
                f.write(f"Test file created at {datetime.datetime.now()}")
            direct_log(f"Successfully wrote test file to: {test_file}")
        except Exception as e:
            direct_log(f"Failed to write test file: {e}")

except Exception as e:
    # Last resort error handling
    print(f"Error during startup: {e}")
    print(traceback.format_exc())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Productivity Tracker")
    app.setQuitOnLastWindowClosed(False)  # Keep app running when windows are closed

    # Create logger for application
    try:
        logger = AppLogger(os.path.join(get_project_root(), 'logs'))
        logger.info("Application startup")
    except Exception as e:
        direct_log(f"Failed to create logger: {e}")
        print(f"Failed to create logger: {e}")

    # Attempt to set system tray visibility settings
    try:
        # Use high-DPI pixmaps for tray icons
        app.setAttribute(QtWidgets.QApplication.AA_UseHighDpiPixmaps)

        # On Windows, try to ensure tray icon is always visible
        import platform

        if platform.system() == "Windows":
            try:
                import win32gui
                import win32con

                direct_log("Windows detected, enhancing system tray visibility")
            except ImportError:
                direct_log("pywin32 not available, system tray icon may not be persistent")
    except Exception as e:
        direct_log(f"Could not set system tray visibility settings: {e}")

    try:
        # Create and show the main window
        direct_log("Creating main window")
        window = MainWindow()
        direct_log("Main window created")

        # Start the application event loop
        direct_log("Starting application event loop")
        sys.exit(app.exec_())
    except Exception as e:
        error_msg = traceback.format_exc()
        direct_log(f"Application failed to start: {error_msg}")

        # Show error dialog
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setText("Application Error")
        error_dialog.setInformativeText(f"The application encountered an error: {str(e)}")
        error_dialog.setDetailedText(error_msg)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()
        sys.exit(1)
