from PyQt5 import QtWidgets
from src.ui.task_dialog import TaskDialog
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os


class TaskManager:
    """
    Handles task creation/management logic separate from UI components.
    This allows both the main window and floating pill to use the same logic.
    """

    def __init__(self, ui_service):
        """Initialize with the UI service."""
        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing Task Manager")

        self.ui_service = ui_service

    def prompt_for_new_task(self, parent_widget):
        """Show dialog to create a new task."""
        try:
            self.logger.debug("Opening task dialog")

            # Create and show the task dialog with the provided parent
            dialog = TaskDialog(parent_widget)
            result = dialog.exec_()

            # If dialog was accepted (OK clicked)
            if result == QtWidgets.QDialog.Accepted:
                task_name, description, category, disable_idle = dialog.get_task_info()

                # Validate task name
                if not task_name:
                    self.logger.warning("Attempted to start task with empty name")
                    QtWidgets.QMessageBox.warning(
                        parent_widget,
                        "Invalid Task",
                        "Task name cannot be empty."
                    )
                    return False

                self.logger.debug(
                    f"Creating new task: '{task_name}', Category: {category}, Disable Idle: {disable_idle}")

                # Start the task in the UI service
                return self.create_task(task_name, description, category, disable_idle)

            return False

        except Exception as e:
            self.logger.error(f"Error in prompt_for_new_task: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

            # Show error to user (Make sure dialog doesn't crash the app)
            try:
                QtWidgets.QMessageBox.critical(
                    parent_widget,
                    "Error Starting Task",
                    f"An error occurred while starting the task: {str(e)}"
                )
            except Exception:
                self.logger.error("Failed to show error dialog")

            return False

    def create_task(self, task_name, description=None, category=None, disable_idle_detection=False):
        """
        Create a new task with the given details.

        Args:
            task_name (str): Name of the task
            description (str, optional): Description of the task
            category (list, optional): Categories or tags for the task
            disable_idle_detection (bool, optional): Disable idle detection

        Returns:
            bool: True if task was created successfully
        """
        try:
            self.logger.debug(f"Creating task: {task_name}, Disable Idle: {disable_idle_detection}")

            # Start the task in the UI service
            success = self.ui_service.start_task(task_name, description, category, disable_idle_detection)

            if success:
                self.logger.info(f"Task '{task_name}' created successfully")
            else:
                self.logger.warning(f"Failed to create task '{task_name}'")

            return success

        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def create_task_dialog_from_pill(self, parent_widget):
        """Special method for creating tasks from the floating pill."""
        try:
            self.logger.debug("Opening task dialog (pill version)")

            # Create and show the task dialog with the provided parent
            dialog = TaskDialog(parent_widget)
            result = dialog.exec_()

            # If dialog was accepted (OK clicked)
            if result == QtWidgets.QDialog.Accepted:
                task_name, description, category, disable_idle = dialog.get_task_info()

                # Validate task name
                if not task_name:
                    self.logger.warning("Attempted to start task with empty name")
                    QtWidgets.QMessageBox.warning(
                        parent_widget,
                        "Invalid Task",
                        "Task name cannot be empty."
                    )
                    return False

                self.logger.debug(
                    f"Creating new task: '{task_name}', Category: {category}, Disable Idle: {disable_idle}")

                # Start the task in the UI service
                return self.create_task(task_name, description, category, disable_idle)

            return False

        except Exception as e:
            self.logger.error(f"Error creating task from pill: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
