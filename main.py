# app.py or main.py in your project root
import sys
from PyQt5 import QtWidgets
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Productivity Tracker")

    # Create and show the main window
    window = MainWindow()

    # The main window will create and show the floating pill
    # Main window is initially hidden per the modifications

    # Start the application event loop
    sys.exit(app.exec_())
