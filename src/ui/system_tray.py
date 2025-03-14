from PyQt5 import QtWidgets, QtGui
from src.utils.time_tracker import TimerState
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os
import sys


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """
    System tray icon and menu for the Productivity Tracker.

    This class handles the system tray integration, providing quick access
    to app functions without needing the main window to be visible.
    """

    def __init__(self, parent=None):
        """
        Initialize the system tray icon.

        Args:
            parent: Parent widget, usually the main window
        """
        super().__init__(parent)

        # Store parent reference explicitly
        self.parent_window = parent
        print(f"Parent window set in __init__: {self.parent_window is not None}")

        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing system tray icon")

        self.setToolTip("Productivity Tracker")

        # Set default icon (stopped state)
        self._set_initial_icon()
        self.logger.debug("System tray icon set")

        # Connect double-click action to toggle window
        self.activated.connect(self._on_activated)

        # Store reference to parent for toggle function
        self.parent_window = parent
        self.toggle_func = None

        # Make sure icon is visible in system tray
        self.setVisible(True)

        self.logger.info("System tray icon initialized")

    def _set_initial_icon(self):
        """Set the initial icon for the system tray"""
        # Try to use custom icon for stopped state
        icon_path = os.path.join(get_project_root(), 'resources', 'tray_icon.png')
        self.logger.debug(f"Attempting to load initial icon from: {icon_path}")

        if os.path.exists(icon_path):
            self.logger.debug(f"Using custom icon from: {icon_path}")
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                self.setIcon(icon)
                return
            else:
                self.logger.warning(f"Icon loaded but is null: {icon_path}")
        else:
            self.logger.warning(f"Custom icon not found: {icon_path}")

        # Fallback to theme or standard icon
        self.logger.warning("Custom icon not found or invalid, using fallback")
        icon = QtGui.QIcon.fromTheme("appointment-soon")
        if icon.isNull():
            # Fallback to a standard icon from the style
            if self.parent_window:
                self.logger.debug("Using fallback icon from parent style")
                icon = self.parent_window.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
            else:
                self.logger.warning("No parent provided for fallback icon")
                # Create a basic icon as last resort
                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(QtGui.QColor(128, 128, 128))
                icon = QtGui.QIcon(pixmap)

        self.setIcon(icon)

    def _get_icon(self, standard_icon):
        """
        Get a standard icon from the parent window or application.

        Args:
            standard_icon: The standard icon identifier from QtWidgets.QStyle

        Returns:
            QIcon: The requested icon
        """
        if self.parent_window:
            return self.parent_window.style().standardIcon(standard_icon)
        else:
            app = QtWidgets.QApplication.instance()
            if app:
                return app.style().standardIcon(standard_icon)
            # Last resort fallback
            self.logger.warning(f"Couldn't get style for icon {standard_icon}")
            return QtGui.QIcon()

    def _on_activated(self, reason):
        """
        Handle tray icon activation (clicks).

        Args:
            reason: Activation reason (e.g., double click)
        """
        # Toggle window visibility on double click
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick and self.toggle_func:
            self.logger.debug("System tray icon double-clicked, toggling window visibility")
            self.toggle_func()
        elif reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.logger.debug("System tray icon single-clicked")
        elif reason == QtWidgets.QSystemTrayIcon.MiddleClick:
            self.logger.debug("System tray icon middle-clicked")
        elif reason == QtWidgets.QSystemTrayIcon.Context:
            self.logger.debug("System tray context menu requested")

    def setup(self, toggle_window_func, start_func, pause_func,
              resume_func, stop_func, sync_func, quit_func):
        """
        Set up the tray icon and menu with the provided callback functions.

        Args:
            toggle_window_func: Function to toggle window visibility
            start_func: Function to start a new task
            pause_func: Function to pause the current task
            resume_func: Function to resume the paused task
            stop_func: Function to stop the current task
            sync_func: Function to sync with Google Sheets
            quit_func: Function to quit the application
        """
        self.logger.info("Setting up system tray menu and actions")

        # Store toggle function for double-click handling
        self.toggle_func = toggle_window_func

        # Create menu
        menu = QtWidgets.QMenu()
        self.logger.debug("Created system tray context menu")

        # Add actions
        toggle_action = menu.addAction("Show/Hide")
        toggle_action.triggered.connect(toggle_window_func)

        menu.addSeparator()

        # Create actions with proper icons using our helper method
        start_action = menu.addAction("Start New Task")
        start_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_MediaPlay))
        start_action.triggered.connect(start_func)

        pause_action = menu.addAction("Pause")
        pause_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_MediaPause))
        pause_action.triggered.connect(pause_func)

        resume_action = menu.addAction("Resume")
        resume_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_MediaPlay))
        resume_action.triggered.connect(resume_func)

        stop_action = menu.addAction("Stop")
        stop_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_MediaStop))
        stop_action.triggered.connect(stop_func)

        menu.addSeparator()

        sync_action = menu.addAction("Sync to Sheets")
        sync_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_ArrowUp))
        sync_action.triggered.connect(sync_func)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.setIcon(self._get_icon(QtWidgets.QStyle.SP_DialogCloseButton))
        # Connect to a proper application exit function
        quit_action.triggered.connect(lambda: self._quit_application(quit_func))

        # Set the context menu
        self.setContextMenu(menu)
        self.logger.debug("Context menu set for system tray icon")

        # Show the icon
        self.show()
        self.logger.info("System tray icon is now visible")

        # Store actions to enable/disable them based on state
        self.actions = {
            'start': start_action,
            'pause': pause_action,
            'resume': resume_action,
            'stop': stop_action,
            'sync': sync_action
        }

        # Set initial action states
        self.update_actions(TimerState.STOPPED)

    def update_actions(self, timer_state):
        """
        Update the enabled state of menu actions based on timer state.

        Args:
            timer_state (TimerState): Current state of the timer
        """
        try:
            self.logger.debug(f"Updating system tray actions for state: {timer_state.name}")

            # Safely check if actions dict exists
            if not hasattr(self, 'actions') or not self.actions:
                self.logger.warning("Actions dict not initialized, can't update actions")
                return

            if timer_state == TimerState.RUNNING:
                # When running, can pause or stop but not start or resume
                self.actions['start'].setEnabled(False)
                self.actions['pause'].setEnabled(True)
                self.actions['resume'].setEnabled(False)
                self.actions['stop'].setEnabled(True)

                # Update tooltip to show currently running task
                if hasattr(self, 'parent_window') and self.parent_window is not None:
                    if hasattr(self.parent_window, 'ui_service'):
                        task_name = self.parent_window.ui_service.get_current_task_name()
                        if task_name:
                            tooltip = f"Productivity Tracker - Running: {task_name}"
                            self.setToolTip(tooltip)
                            self.logger.debug(f"Updated tooltip: {tooltip}")

                # Change tray icon to indicate running state
                self.logger.debug(f"Setting icon for state: {timer_state.name}")
                self._set_icon_for_state(timer_state)

            elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
                # When paused/idle, can resume or stop but not start or pause
                self.actions['start'].setEnabled(False)
                self.actions['pause'].setEnabled(False)
                self.actions['resume'].setEnabled(True)
                self.actions['stop'].setEnabled(True)

                # Update tooltip to show paused state
                if hasattr(self, 'parent_window') and self.parent_window is not None:
                    if hasattr(self.parent_window, 'ui_service'):
                        task_name = self.parent_window.ui_service.get_current_task_name()
                        if task_name:
                            state_text = "Paused" if timer_state == TimerState.PAUSED else "Idle"
                            tooltip = f"Productivity Tracker - {state_text}: {task_name}"
                            self.setToolTip(tooltip)
                            self.logger.debug(f"Updated tooltip: {tooltip}")

                # Change tray icon to indicate paused/idle state
                self.logger.debug(f"Setting icon for state: {timer_state.name}")
                self._set_icon_for_state(timer_state)

            elif timer_state == TimerState.STOPPED:
                # When stopped, can only start a new task
                self.actions['start'].setEnabled(True)
                self.actions['pause'].setEnabled(False)
                self.actions['resume'].setEnabled(False)
                self.actions['stop'].setEnabled(False)

                # Reset tooltip
                self.setToolTip("Productivity Tracker - Ready")
                self.logger.debug("Reset tooltip to default (Ready)")

                # Reset icon
                self.logger.debug(f"Setting icon for state: {timer_state.name}")
                self._set_icon_for_state(timer_state)

            # Sync button is always enabled if there are unsynced tasks
            if hasattr(self, 'parent_window') and self.parent_window is not None:
                if hasattr(self.parent_window, 'ui_service'):
                    try:
                        unsynced_count = self.parent_window.ui_service.get_unsynced_tasks_count()
                        self.actions['sync'].setEnabled(unsynced_count > 0)

                        # Update tooltip to show sync status
                        if unsynced_count > 0:
                            current_tooltip = self.toolTip()
                            tooltip = f"{current_tooltip} ({unsynced_count} tasks pending sync)"
                            self.setToolTip(tooltip)
                            self.logger.debug(f"Updated tooltip with sync info: {tooltip}")
                    except Exception as e:
                        self.logger.error(f"Error getting unsynced task count: {e}")
        except Exception as e:
            print(f"Error in update_actions: {e}")  # Print to console regardless of logger
            if hasattr(self, 'logger'):
                self.logger.error(f"Error updating system tray actions: {e}")

    def _set_icon_for_state(self, state):
        """
        Set the system tray icon based on the current timer state.

        Args:
            state (TimerState): Current state of the timer
        """
        try:
            # Print to console for debugging regardless of logger
            print(f"Setting system tray icon for state: {state.name}")

            if hasattr(self, 'logger'):
                self.logger.debug(f"Setting system tray icon for state: {state.name}")

            # Default to using a colored pixmap if resources can't be loaded
            if state == TimerState.RUNNING:
                color = QtGui.QColor(0, 255, 0)  # Green for running
                icon_name = "tray_icon_running.png"
            elif state in [TimerState.PAUSED, TimerState.IDLE]:
                color = QtGui.QColor(255, 165, 0)  # Orange for paused/idle
                icon_name = "tray_icon_idle.png"
            else:  # STOPPED or any other state
                color = QtGui.QColor(128, 128, 128)  # Gray for stopped
                icon_name = "tray_icon.png"

            # Try different paths to find the icon
            icon_found = False

            # Path options to try
            paths_to_try = [
                # Try executable directory first for packaged app
                os.path.join(os.path.dirname(sys.executable), "resources", icon_name),
                # Try current directory
                os.path.join("resources", icon_name),
                # Try absolute path via a function
                None  # Will be replaced by get_project_root path if available
            ]

            # Try to add path from get_project_root
            try:
                from src.utils.path_utils import get_project_root
                project_root = get_project_root()
                if project_root:
                    paths_to_try[2] = os.path.join(project_root, "resources", icon_name)
            except Exception as e:
                print(f"Error getting project root: {e}")
                # Keep None as a placeholder

            # Try each path until an icon is found
            for path in paths_to_try:
                if path is None:
                    continue

                try:
                    print(f"Trying icon path: {path}")
                    if os.path.exists(path):
                        icon = QtGui.QIcon(path)
                        if not icon.isNull():
                            self.setIcon(icon)
                            print(f"Successfully set icon from: {path}")
                            icon_found = True
                            break
                except Exception as e:
                    print(f"Error loading icon from {path}: {e}")

            # If no icon was found, create a colored rectangle
            if not icon_found:
                print("No icon found, creating colored pixmap")
                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(color)
                icon = QtGui.QIcon(pixmap)
                self.setIcon(icon)

        except Exception as e:
            print(f"Error in _set_icon_for_state: {e}")
            # Create a fallback icon as last resort
            try:
                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(QtGui.QColor(255, 0, 0))  # Red for error
                icon = QtGui.QIcon(pixmap)
                self.setIcon(icon)
            except:
                print("Failed to create even a fallback icon")

    def show_message(self, title, message, icon=QtWidgets.QSystemTrayIcon.Information, duration=5000):
        """
        Show a notification message from the system tray.

        Args:
            title (str): Title of the notification
            message (str): Message content
            icon (QSystemTrayIcon.MessageIcon): Icon type to show
            duration (int): Duration in milliseconds to show the message
        """
        self.logger.info(f"Showing system tray notification: {title} - {message}")

        # Check if we support notifications
        if not self.supportsMessages():
            self.logger.warning("System does not support tray notifications")
            return False

        self.showMessage(title, message, icon, duration)
        return True

    def _quit_application(self, quit_func):
        """
        Properly quit the application from the system tray.

        Args:
            quit_func: Function passed from main window to handle closing
        """
        self.logger.info("Quitting application from system tray")

        # First try to use the provided quit function which should handle any cleanup
        try:
            if quit_func and callable(quit_func):
                quit_func()
        except Exception as e:
            self.logger.error(f"Error in quit function: {e}")

        # Ensure application truly quits
        app = QtWidgets.QApplication.instance()
        if app:
            self.logger.info("Calling QApplication.quit()")
            app.quit()
        else:
            # Fallback to sys.exit if QApplication instance not found
            self.logger.info("QApplication instance not found, using sys.exit()")
            import sys
            sys.exit(0)
