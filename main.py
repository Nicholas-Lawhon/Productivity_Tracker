# app.py or main.py in your project root
import sys
import traceback
from PyQt5 import QtWidgets
from src.ui.main_window import MainWindow
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os


def exception_hook(exctype, value, tb):
    """
    Global exception handler to log unhandled exceptions
    """
    logger = AppLogger(os.path.join(get_project_root(), 'logs'))
    logger.critical(f"UNHANDLED EXCEPTION: {exctype.__name__}: {value}")
    logger.critical("".join(traceback.format_exception(exctype, value, tb)))
    sys.__excepthook__(exctype, value, tb)  # Call the original exception handler


if __name__ == "__main__":
    # Install global exception handler
    sys.excepthook = exception_hook

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Productivity Tracker")

    try:
        # Create and show the main window
        window = MainWindow()

        # Start the application event loop
        sys.exit(app.exec_())
    except Exception as e:
        logger = AppLogger(os.path.join(get_project_root(), 'logs'))
        logger.critical(f"Application failed to start: {e}")
        logger.critical(traceback.format_exc())

        # Show error dialog
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setText("Application Error")
        error_dialog.setInformativeText(f"The application encountered an error: {str(e)}")
        error_dialog.setDetailedText(traceback.format_exc())
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()
        sys.exit(1)
