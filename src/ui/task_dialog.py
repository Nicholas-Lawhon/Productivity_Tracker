from PyQt5 import QtWidgets, QtCore, QtGui
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os


class TaskDialog(QtWidgets.QDialog):
    """
    Dialog for entering a new task to track.

    This dialog allows the user to enter a task name and optional description
    when starting a new productivity tracking session.
    """

    def __init__(self, parent=None):
        """
        Initialize the task dialog.

        Args:
            parent: Parent widget, if any
        """
        super().__init__(parent)

        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.debug("Initializing task entry dialog")

        self.setWindowTitle("New Task")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        # Set up the UI components
        self.setup_ui()

        # Focus the task name input field when dialog opens
        self.task_name_input.setFocus()

        self.logger.debug("Task dialog initialized")

    def setup_ui(self):
        """
        Set up the dialog's user interface.
        """
        self.logger.debug("Setting up task dialog UI")

        # Create layout
        layout = QtWidgets.QVBoxLayout()

        # Create form layout for inputs
        form_layout = QtWidgets.QFormLayout()

        # Add task name input
        self.task_name_input = QtWidgets.QLineEdit()
        self.task_name_input.setPlaceholderText("Enter task name here")
        form_layout.addRow("Task Name:", self.task_name_input)

        # Add description input
        self.description_input = QtWidgets.QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Optional: Enter additional details about this task")
        form_layout.addRow("Description (optional):", self.description_input)

        # Create a scroll area for checkboxes to support many tags
        self.category_frame = QtWidgets.QFrame()
        self.category_frame.setMaximumHeight(120)
        self.category_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Container widget for checkboxes
        checkbox_container = QtWidgets.QWidget()
        self.category_layout = QtWidgets.QVBoxLayout(checkbox_container)

        # These should be fetched from somewhere, but for now we'll hardcode
        self.categories = ["Chill", "Gaming", "Leetcode", "Personal Project", "School", "Self-learning", "Other", "None"]
        self.category_checkboxes = {}

        # Idle Detection checkbox
        self.disable_idle_checkbox = QtWidgets.QCheckBox("Disable Idle Detection")
        self.disable_idle_checkbox.setToolTip(
            "Check this if you don't want the timer to pause when you're inactive (e.g., watching videos)")
        layout.addWidget(self.disable_idle_checkbox)

        for category in self.categories:
            checkbox = QtWidgets.QCheckBox(category)
            self.category_layout.addWidget(checkbox)
            self.category_checkboxes[category] = checkbox

        # Add a bit of spacing at the bottom
        self.category_layout.addStretch()

        # Set up the scroll area
        scroll_area.setWidget(checkbox_container)
        scroll_layout = QtWidgets.QVBoxLayout(self.category_frame)
        scroll_layout.addWidget(scroll_area)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        form_layout.addRow("Tags (select multiple):", self.category_frame)

        # Add form to main layout
        layout.addLayout(form_layout)

        # Add validation feedback label
        self.feedback_label = QtWidgets.QLabel("")
        self.feedback_label.setStyleSheet("color: red;")
        self.feedback_label.setVisible(False)
        layout.addWidget(self.feedback_label)

        # Add standard buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Set dialog layout
        self.setLayout(layout)

        # Set minimum width
        self.setMinimumWidth(400)

        # Connect validation
        self.task_name_input.textChanged.connect(self.validate_input)

        self.logger.debug("Task dialog UI setup complete")

    def validate_input(self):
        """
        Validate the input fields and update UI feedback.
        """
        task_name = self.task_name_input.text().strip()

        if not task_name:
            self.feedback_label.setText("Task name is required")
            self.feedback_label.setVisible(True)
            self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.feedback_label.setVisible(False)
            self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def validate_and_accept(self):
        """
        Validate input before accepting the dialog.
        """
        task_name = self.task_name_input.text().strip()

        if not task_name:
            self.logger.warning("Attempted to submit task with empty name")
            self.feedback_label.setText("Task name is required")
            self.feedback_label.setVisible(True)
            return

        # Get selected categories for logging
        selected_categories = [cat for cat, checkbox in self.category_checkboxes.items()
                               if checkbox.isChecked()]

        self.logger.info(f"New task created: '{task_name}' with tags: {selected_categories}")
        self.accept()

    def get_task_info(self):
        """
        Get the entered task information.

        Returns:
            tuple: (task_name, description, categories, disable_idle_detection)
        """
        task_name = self.task_name_input.text().strip()
        description = self.description_input.toPlainText().strip()

        # Get selected categories
        selected_categories = [cat for cat, checkbox in self.category_checkboxes.items()
                               if checkbox.isChecked()]

        # Get idle detection setting
        disable_idle_detection = self.disable_idle_checkbox.isChecked()

        # Join selected categories with commas for easier storage/display
        categories_str = ", ".join(selected_categories)

        self.logger.debug(
            f"Task info retrieved - Name: '{task_name}', Tags: {categories_str}, Disable Idle: {disable_idle_detection}")

        return task_name, description, selected_categories, disable_idle_detection

    def closeEvent(self, event):
        """
        Handle dialog close event.

        Args:
            event: Close event
        """
        self.logger.debug("Task dialog closed")
        super().closeEvent(event)

    def reject(self):
        """
        Handle dialog rejection (Cancel button or Escape key).
        """
        self.logger.debug("Task creation cancelled by user")
        super().reject()