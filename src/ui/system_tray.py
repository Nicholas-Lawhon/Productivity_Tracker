from PyQt5 import QtWidgets, QtGui
from src.utils.time_tracker import TimerState
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
import os


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

        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing system tray icon")

        self.setToolTip("Productivity Tracker")

        # Set a default icon if theme icon is not available
        icon = QtGui.QIcon.fromTheme("appointment-soon")
        if icon.isNull():
            # Fallback to a standard icon from the style
            if parent:
                self.logger.debug("Using fallback icon from parent style")
                icon = parent.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
            else:
                self.logger.warning("No parent provided for fallback icon")

        self.setIcon(icon)
        self.logger.debug("System tray icon set")

        # Connect double-click action to toggle window
        self.activated.connect(self._on_activated)

        # Store reference to parent for toggle function
        self.parent_window = parent
        self.toggle_func = None

        self.logger.info("System tray icon initialized")

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
        quit_action.triggered.connect(quit_func)

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
        self.logger.debug(f"Updating system tray actions for state: {timer_state.name}")

        if timer_state == TimerState.RUNNING:
            # When running, can pause or stop but not start or resume
            self.actions['start'].setEnabled(False)
            self.actions['pause'].setEnabled(True)
            self.actions['resume'].setEnabled(False)
            self.actions['stop'].setEnabled(True)

            # Update tooltip to show currently running task
            if hasattr(self.parent_window, 'ui_service'):
                task_name = self.parent_window.ui_service.get_current_task_name()
                if task_name:
                    tooltip = f"Productivity Tracker - Running: {task_name}"
                    self.setToolTip(tooltip)
                    self.logger.debug(f"Updated tooltip: {tooltip}")

            # Change tray icon to indicate running state
            self._set_icon_for_state(timer_state)

        elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
            # When paused/idle, can resume or stop but not start or pause
            self.actions['start'].setEnabled(False)
            self.actions['pause'].setEnabled(False)
            self.actions['resume'].setEnabled(True)
            self.actions['stop'].setEnabled(True)

            # Update tooltip to show paused state
            if hasattr(self.parent_window, 'ui_service'):
                task_name = self.parent_window.ui_service.get_current_task_name()
                if task_name:
                    state_text = "Paused" if timer_state == TimerState.PAUSED else "Idle"
                    tooltip = f"Productivity Tracker - {state_text}: {task_name}"
                    self.setToolTip(tooltip)
                    self.logger.debug(f"Updated tooltip: {tooltip}")

            # Change tray icon to indicate paused/idle state
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
            self._set_icon_for_state(timer_state)

        # Sync button is always enabled if there are unsynced tasks
        if hasattr(self.parent_window, 'ui_service'):
            unsynced_count = self.parent_window.ui_service.get_unsynced_tasks_count()
            self.actions['sync'].setEnabled(unsynced_count > 0)

            # Update tooltip to show sync status
            if unsynced_count > 0:
                current_tooltip = self.toolTip()
                tooltip = f"{current_tooltip} ({unsynced_count} tasks pending sync)"
                self.setToolTip(tooltip)
                self.logger.debug(f"Updated tooltip with sync info: {tooltip}")

    def _set_icon_for_state(self, state):
        """
        Set the system tray icon based on the current timer state.

        Args:
            state (TimerState): Current state of the timer
        """
        self.logger.debug(f"Setting system tray icon for state: {state.name}")

        # Create colored icons for different states
        # This is a simple approach - for production, you'd use actual icon files

        if state == TimerState.RUNNING:
            # Try to use a "running" themed icon
            icon = QtGui.QIcon.fromTheme("media-playback-start")
            if icon.isNull():
                # Or create a colored icon (green)
                self.logger.debug("Creating green icon for running state")
                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(QtGui.QColor(0, 255, 0))
                icon = QtGui.QIcon(pixmap)

        elif state in [TimerState.PAUSED, TimerState.IDLE]:
            # Try to use a "paused" themed icon
            icon = QtGui.QIcon.fromTheme("media-playback-pause")
            if icon.isNull():
                # Or create a colored icon (yellow for pause, orange for idle)
                color_name = "yellow" if state == TimerState.PAUSED else "orange"
                self.logger.debug(f"Creating {color_name} icon for {state.name} state")
                pixmap = QtGui.QPixmap(16, 16)
                color = QtGui.QColor(255, 255, 0) if state == TimerState.PAUSED else QtGui.QColor(255, 165, 0)
                pixmap.fill(color)
                icon = QtGui.QIcon(pixmap)

        else:  # STOPPED
            # Use default icon
            icon = QtGui.QIcon.fromTheme("appointment-soon")
            if icon.isNull():
                # Fallback
                self.logger.debug("Using fallback icon for stopped state")
                if self.parent_window:
                    icon = self.parent_window.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
                else:
                    self.logger.warning("No parent provided for fallback icon")

        # Set the icon if we found/created one
        if not icon.isNull():
            self.setIcon(icon)
            self.logger.debug("System tray icon updated successfully")
        else:
            self.logger.warning("Failed to create icon for system tray")

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
