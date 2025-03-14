from PyQt5 import QtWidgets, QtCore, QtGui
from src.utils.time_tracker import TimerState, PauseReason, TimeTracker
from src.services.ui_service import UIService
from src.services.task_manager import TaskManager
from src.ui.system_tray import SystemTrayIcon
from src.ui.task_dialog import TaskDialog
from src.utils.logger import AppLogger
from src.ui.floating_pill import FloatingPillWidget
from src.utils.path_utils import get_project_root
import os


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window for the Productivity Tracker App.

    This class handles the primary user interface, including the timer display,
    task controls, and system tray integration.
    """

    def __init__(self, parent=None):
        """
        Initialize the main window and connect to services.

        Args:
            parent: Parent widget, if any
        """
        super().__init__(parent)

        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing main window")

        # Initialize services
        self.ui_service = UIService()
        self.task_manager = TaskManager(self.ui_service)

        # Connect callbacks from service to UI methods
        self.ui_service.register_state_change_callback(self.handle_state_change)
        self.ui_service.register_idle_callback(self.handle_idle_detected)
        self.ui_service.register_long_pause_callback(self.handle_long_pause)
        self.logger.debug("Connected UI service callbacks")

        # Set up UI components
        self.setup_ui()
        self.logger.debug("UI components initialized")

        # Initialize system tray
        print("About to initialize system tray icon")
        self.system_tray = SystemTrayIcon(self)
        print("System tray icon initialized")

        # Verify parent is properly set
        print(f"Parent set: {self.system_tray.parent_window is not None}")
        print(f"Parent is self: {self.system_tray.parent_window is self}")
        self.system_tray.setup(self.toggle_window_visibility,
                               self.start_task_dialog,
                               self.pause_task,
                               self.resume_task,
                               self.stop_task,
                               self.sync_to_sheets,
                               self.close)
        self.logger.debug("System tray initialized")

        # Ensure system tray icon is visible
        self.system_tray.show()

        # Make sure the main window is visible and active
        self.show()
        self.raise_()
        self.activateWindow()

        # Update the system tray icon to reflect current state
        if hasattr(self, 'ui_service'):
            current_state = self.ui_service.get_timer_state()
            self.system_tray.update_actions(current_state)

        # If we started minimized to system tray, hide the main window
        if os.environ.get('START_MINIMIZED') == '1':
            self.hide()
        else:
            # Otherwise make sure the main window is visible and active
            self.show()
            self.raise_()
            self.activateWindow()

        # Update the system tray icon to reflect current state
        if self.ui_service:
            current_state = self.ui_service.get_timer_state()
            self.system_tray.update_actions(current_state)

        # Call test_icons to ensure icons are loaded properly
        # self.system_tray.test_icons()  # Uncomment for debugging if needed

        # Window properties
        self.setWindowTitle("Productivity Tracker")
        self.resize(400, 200)

        # Update unsynced tasks count
        self.update_sync_status()
        self.logger.info("Main window initialization complete")

        # Initialize the dockable floating pill as a separate window
        self.floating_pill = FloatingPillWidget(self)
        # Make sure it's a top-level window
        self.floating_pill.setParent(None)
        # Force a position in the visible area of the screen before showing
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.floating_pill.move((screen.width() - self.floating_pill.width()) // 2, 40)
        # Set the proper size - ensure it's wide enough
        self.floating_pill.resize(320, 40)
        # Show the floating pill
        self.floating_pill.show()
        # Ensure the floating pill is brought to front
        self.floating_pill.raise_()

        # Start with main window hidden
        self.hide()

    def setup_ui(self):
        """
        Set up the main user interface components including layout and widgets.
        """
        # Central widget
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Task information section
        self.task_frame = QtWidgets.QGroupBox("Current Task")
        task_layout = QtWidgets.QVBoxLayout(self.task_frame)

        self.task_name_label = QtWidgets.QLabel("No task running")
        self.task_name_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        task_layout.addWidget(self.task_name_label)

        self.timer_label = QtWidgets.QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        task_layout.addWidget(self.timer_label)

        self.main_layout.addWidget(self.task_frame)

        # Control buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.start_button = QtWidgets.QPushButton("Start New Task")
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        button_layout.addWidget(self.start_button)

        self.pause_resume_button = QtWidgets.QPushButton("Pause")
        self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        self.pause_resume_button.setEnabled(False)
        button_layout.addWidget(self.pause_resume_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.main_layout.addLayout(button_layout)

        # Status section
        self.status_frame = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QHBoxLayout(self.status_frame)

        self.status_label = QtWidgets.QLabel("Ready")
        status_layout.addWidget(self.status_label)

        self.sync_status = QtWidgets.QLabel("0 tasks pending sync")
        self.sync_status.setAlignment(QtCore.Qt.AlignRight)
        status_layout.addWidget(self.sync_status)

        self.sync_button = QtWidgets.QPushButton("Sync to Sheets")
        self.sync_button.setEnabled(False)
        status_layout.addWidget(self.sync_button)

        self.main_layout.addWidget(self.status_frame)

        # Setup timer for updates
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second

        # Connect buttons
        self.start_button.clicked.connect(self.start_task_dialog)
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.stop_button.clicked.connect(self.stop_task)
        self.sync_button.clicked.connect(self.sync_to_sheets)

    def handle_state_change(self, new_state):
        """
        Update UI when the timer state changes.

        Args:
            new_state (TimerState): The new state of the timer
        """
        self.logger.debug(f"Timer state changed to: {new_state.name}")

        # Preserve task name even during idle
        current_task = self.ui_service.get_current_task_name()

        # Update status label based on new state
        if new_state == TimerState.RUNNING:
            self.status_label.setText("Running")
            # Update the pause/resume button to show "Pause"
            self.pause_resume_button.setText("Pause")
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))

            # Enable control buttons
            self.pause_resume_button.setEnabled(True)
            self.stop_button.setEnabled(True)

            self.logger.info(f"Timer started for task: '{current_task}'")

        elif new_state == TimerState.PAUSED:
            self.status_label.setText("Paused (User)")
            # Update the pause/resume button to show "Resume"
            self.pause_resume_button.setText("Resume")
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))

            self.logger.info("Timer paused by user")

        elif new_state == TimerState.IDLE:
            self.status_label.setText("Paused (Idle)")
            # Update the pause/resume button to show "Resume"
            self.pause_resume_button.setText("Resume")
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))

            self.logger.info("Timer paused due to system idle")

        elif new_state == TimerState.STOPPED:
            self.status_label.setText("Ready")
            # Reset task name and disable buttons
            self.task_name_label.setText("No task running")
            self.pause_resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)

            self.logger.info("Timer stopped")

            # Check if we need to update sync status after stopping
            self.update_sync_status()

        # If the system tray is initialized, update its action states
        if hasattr(self, 'system_tray'):
            self.system_tray.update_actions(new_state)

    def handle_idle_detected(self):
        """
        Handle system idle detection, update UI and show notification.
        """
        self.logger.info("System idle detected, timer paused automatically")

        # Change status label to indicate idle state
        self.status_label.setText("Paused (Idle detected)")

        # Change the background color to visually indicate idle state
        self.task_frame.setStyleSheet("QGroupBox { background-color: #FFEEEE; }")

        # Show a popup dialog
        task_name = self.ui_service.get_current_task_name()

        # Use a non-modal dialog so it doesn't block the application
        idle_dialog = QtWidgets.QMessageBox(self)
        idle_dialog.setWindowTitle("Productivity Tracker")
        idle_dialog.setText("Idle Detected")

        # Include the task name in the message
        if task_name:
            idle_dialog.setInformativeText(
                f"Timer for task \"{task_name}\" has been paused due to inactivity.\n"
                "Click 'Resume' to continue tracking."
            )
        else:
            idle_dialog.setInformativeText(
                "Timer has been paused due to inactivity.\n"
                "Click 'Resume' to continue tracking."
            )

        idle_dialog.setIcon(QtWidgets.QMessageBox.Information)

        # Add Resume button
        resume_button = idle_dialog.addButton("Resume", QtWidgets.QMessageBox.AcceptRole)
        idle_dialog.addButton("Dismiss", QtWidgets.QMessageBox.RejectRole)

        # Make the dialog non-modal so it doesn't block the application
        idle_dialog.setWindowModality(QtCore.Qt.NonModal)

        # Show the dialog
        idle_dialog.show()

        # Connect the clicked signal of the Resume button
        resume_button.clicked.connect(self.resume_task)

    def handle_long_pause(self, duration):
        """
        Handle when the timer has been paused for too long.

        Args:
            duration (float): The duration of the pause in seconds
        """
        # Format duration in minutes for display
        minutes = int(duration / 60)

        self.logger.warning(f"Timer has been paused for {minutes} minutes")

        # Highlight the status label to draw attention
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_label.setText(f"Paused for {minutes} min!")

        # Flash the window to get user's attention if it's not active
        if not self.isActiveWindow() and self.isVisible():
            QtWidgets.QApplication.alert(self)

    # In MainWindow class
    def start_task_dialog(self):
        """Show dialog to enter a new task and start the timer."""
        try:
            self.logger.debug("Opening task dialog")

            # Create and show the task dialog
            dialog = TaskDialog(self)
            result = dialog.exec_()

            # If dialog was accepted (OK clicked)
            if result == QtWidgets.QDialog.Accepted:
                task_name, description, category, disable_idle = dialog.get_task_info()

                # Validate task name
                if not task_name:
                    self.logger.warning("Attempted to start task with empty name")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Invalid Task",
                        "Task name cannot be empty."
                    )
                    return

                self.logger.debug(
                    f"Starting new task: '{task_name}', Category: {category}, Disable Idle: {disable_idle}")

                # Start the task directly
                self.start_task(task_name, description, category, disable_idle)

        except Exception as e:
            self.logger.error(f"Error in start_task_dialog: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

            # Show error to user
            QtWidgets.QMessageBox.critical(
                self,
                "Error Starting Task",
                f"An error occurred while starting the task: {str(e)}"
            )

    def start_task(self, task_name, description=None, category=None, disable_idle=False):
        """Start the timer with the given task name."""
        try:
            self.logger.debug(
                f"Starting task: {task_name}, description: {description}, category: {category}, disable_idle: {disable_idle}")

            # Start the task in the service
            success = self.ui_service.start_task(task_name, description, category, disable_idle)

            if success:
                # Update UI with new task
                self.task_name_label.setText(task_name)

                # Enable control buttons
                self.pause_resume_button.setEnabled(True)
                self.stop_button.setEnabled(True)

                # Reset any warning styles
                self.status_label.setStyleSheet("")
                self.task_frame.setStyleSheet("")

            return success
        except Exception as e:
            self.logger.error(f"Error in start_task: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

            # Show error to user
            QtWidgets.QMessageBox.critical(
                self,
                "Error Starting Task",
                f"An error occurred while starting the task: {str(e)}"
            )
            return False

    def toggle_pause_resume(self):
        """
        Toggle between pause and resume based on current timer state.
        """
        if self.ui_service.time_tracker.state == TimerState.RUNNING:
            self.pause_task()
        else:
            self.resume_task()

    def pause_task(self):
        """
        Pause the currently running task.
        """
        self.logger.debug("Pause requested")

        # Call service to pause the task
        success = self.ui_service.pause_task()

        if success:
            self.logger.debug("Task paused successfully")
            # UI will be updated in handle_state_change when callback is triggered
        else:
            self.logger.warning("Failed to pause task")

        # Note: We don't need to manually update UI here because handle_state_change
        # will be called from the time_tracker via ui_service callbacks

    def resume_task(self):
        """
        Resume the currently paused task.
        """
        self.logger.debug("Resume requested")

        # Call service to resume the task
        success = self.ui_service.resume_task()

        if success:
            self.logger.debug("Task resumed successfully")
            # Reset any warning styles that might have been applied
            self.status_label.setStyleSheet("")
            self.task_frame.setStyleSheet("")
        else:
            self.logger.warning("Failed to resume task")

        # Note: handle_state_change will be called to update UI elements

    def stop_task(self):
        """
        Stop the current task, save to database, and reset the UI.
        """
        self.logger.debug("Stop task requested")

        # Ask for confirmation
        reply = QtWidgets.QMessageBox.question(
            self,
            'Confirm Stop',
            'Are you sure you want to stop the current task?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.logger.info("Stopping current task")

            # Stop the task and save to database
            result = self.ui_service.stop_task()

            if result:
                self.logger.info("Task stopped and saved to database")

                # Update sync status since we added a new task
                self.update_sync_status()

                # Ask if user wants to sync now
                self.ask_to_sync()
            else:
                self.logger.warning("Failed to stop task or no task was running")

    def ask_to_sync(self):
        """
        Ask the user if they want to sync tasks to Google Sheets now.
        """
        unsynced_count = self.ui_service.get_unsynced_tasks_count()

        if unsynced_count > 0:
            reply = QtWidgets.QMessageBox.question(
                self,
                'Sync to Google Sheets',
                f'You have {unsynced_count} unsynced tasks. Sync to Google Sheets now?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )

            if reply == QtWidgets.QMessageBox.Yes:
                # Create a separate non-blocking timer to call sync
                # This prevents the sync action from being in the same call stack as the dialog
                QtCore.QTimer.singleShot(100, self.sync_to_sheets)

    def toggle_window_visibility(self):
        """
        Toggle between visible and minimized to system tray.
        """
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            self.activateWindow()  # Bring window to front

    def sync_to_sheets(self):
        """
        Sync unsynced tasks to Google Sheets.
        """
        self.logger.info("Starting sync to Google Sheets")

        # Show a progress dialog
        progress_dialog = QtWidgets.QProgressDialog("Syncing to Google Sheets...", "Cancel", 0, 0, self)
        progress_dialog.setWindowTitle("Syncing")
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.show()

        # Create a separate thread for sync operation
        QtCore.QTimer.singleShot(100, lambda: self._do_sync(progress_dialog))

    def _do_sync(self, progress_dialog):
        """
        Perform the actual sync operation and update UI when complete.

        Args:
            progress_dialog (QProgressDialog): Progress dialog to close when done
        """
        try:
            # Perform sync operation
            success = self.ui_service.sync_to_sheets()

            # Close progress dialog
            progress_dialog.close()

            # Show result
            if success:
                self.logger.info("Tasks successfully synced to Google Sheets")
                message_box = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Information,
                    "Sync Complete",
                    "Tasks successfully synced to Google Sheets.",
                    QtWidgets.QMessageBox.Ok,
                    self
                )
                message_box.exec_()
            else:
                self.logger.warning("Failed to sync tasks to Google Sheets")
                message_box = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Warning,
                    "Sync Failed",
                    "Failed to sync tasks to Google Sheets.",
                    QtWidgets.QMessageBox.Ok,
                    self
                )
                message_box.exec_()

            # Update sync status
            self.update_sync_status()

        except Exception as e:
            self.logger.error(f"Error during sync: {str(e)}")
            progress_dialog.close()
            message_box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Critical,
                "Sync Error",
                f"An error occurred while syncing: {str(e)}",
                QtWidgets.QMessageBox.Ok,
                self
            )
            message_box.exec_()

    def update_sync_status(self):
        """
        Update the sync status label and button based on unsynced tasks.
        """
        # Get count of unsynced tasks
        unsynced_count = self.ui_service.get_unsynced_tasks_count()

        self.logger.debug(f"Updating sync status: {unsynced_count} tasks pending sync")

        # Update sync status label
        self.sync_status.setText(f"{unsynced_count} tasks pending sync")

        # Enable sync button if there are unsynced tasks
        self.sync_button.setEnabled(unsynced_count > 0)

    def update_display(self):
        """
        Update the timer display with current elapsed time.
        Called every second by the update_timer.
        """
        # Get formatted elapsed time
        elapsed_time = self.ui_service.get_elapsed_time_formatted()

        # Update the timer label
        self.timer_label.setText(elapsed_time)

        # Check for idle if timer is running
        if self.ui_service.time_tracker.state == TimerState.RUNNING:
            self.ui_service.time_tracker.check_idle()

        # Check for long pause if timer is paused
        if self.ui_service.time_tracker.state in [TimerState.PAUSED, TimerState.IDLE]:
            self.ui_service.time_tracker.check_long_pause()

        # Log elapsed time every minute (to avoid excessive logging)
        seconds = int(self.ui_service.time_tracker.get_elapsed_time())
        if seconds % 60 == 0 and seconds > 0 and self.ui_service.time_tracker.state == TimerState.RUNNING:
            task_name = self.ui_service.get_current_task_name()
            minutes = seconds // 60
            self.logger.debug(f"Task '{task_name}' running for {minutes} minutes")

    def closeEvent(self, event):
        """
        Handle window close event, check if timer is running.

        Args:
            event (QCloseEvent): The close event
        """
        self.logger.debug("Application close requested")

        # If timer is running, ask for confirmation
        if self.ui_service.is_timer_running():
            self.logger.info("Timer still running on exit - prompting user")
            reply = QtWidgets.QMessageBox.question(
                self,
                'Confirm Exit',
                'Timer is still running. Do you want to exit anyway?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.logger.info("User confirmed exit with timer running - stopping timer")
                # Stop the timer and save the task
                self.ui_service.stop_task()
                event.accept()
            else:
                self.logger.info("Exit cancelled - timer still running")
                # Cancel the close event
                event.ignore()
        else:
            # Check for unsynced tasks and offer to sync
            unsynced_count = self.ui_service.get_unsynced_tasks_count()
            if unsynced_count > 0:
                self.logger.info(f"Unsynced tasks on exit: {unsynced_count} - prompting user")
                reply = QtWidgets.QMessageBox.question(
                    self,
                    'Unsynced Tasks',
                    f'You have {unsynced_count} unsynced tasks. Sync before exiting?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                    QtWidgets.QMessageBox.Yes
                )

                if reply == QtWidgets.QMessageBox.Yes:
                    self.logger.info("User chose to sync before exit")
                    # Sync but don't automatically exit (remove auto-termination)
                    self.sync_to_sheets()
                    # Only now accept the event
                    event.accept()
                elif reply == QtWidgets.QMessageBox.No:
                    self.logger.info("User chose to exit without syncing")
                    # Just accept the close event
                    event.accept()
                else:  # Cancel
                    self.logger.info("Exit cancelled due to pending syncs")
                    event.ignore()
            else:
                self.logger.info("Application closing - no issues")
                # No issues, accept the close event
                event.accept()

        if event.isAccepted():
            # Show a final confirmation for quitting vs minimizing
            reply = QtWidgets.QMessageBox.question(
                self,
                'Exit or Minimize',
                'Do you want to exit the application completely?\n\n'
                'Click "Yes" to exit completely.\n'
                'Click "No" to minimize to system tray.',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.logger.info("User chose to exit application completely")
                # Explicitly quit the application
                QtWidgets.QApplication.instance().quit()
            else:
                self.logger.info("User chose to minimize to system tray")
                # Prevent the default close and just hide the window
                event.ignore()
                self.hide()

    def start_task_from_pill(self):
        """Special method to be called by the floating pill to start a new task."""
        self.logger.debug("Starting task from floating pill")

        # Show the task dialog directly from here
        dialog = TaskDialog(self)
        result = dialog.exec_()

        # If dialog was accepted (OK clicked)
        if result == QtWidgets.QDialog.Accepted:
            task_name, description, category, disable_idle = dialog.get_task_info()

            # Validate task name
            if not task_name:
                self.logger.warning("Attempted to start task with empty name")
                return

            # Start the task directly
            self.ui_service.start_task(task_name, description, category, disable_idle)

            # Update UI
            self.task_name_label.setText(task_name)
            self.pause_resume_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.status_label.setStyleSheet("")
            self.task_frame.setStyleSheet("")

    def update_ui_for_running_task(self, task_name):
        """Update UI elements when a task starts."""
        # Update UI with new task
        self.task_name_label.setText(task_name)

        # Enable control buttons
        self.pause_resume_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        # Reset any warning styles
        self.status_label.setStyleSheet("")
        self.task_frame.setStyleSheet("")
