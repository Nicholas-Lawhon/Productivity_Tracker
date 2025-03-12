from PyQt5 import QtWidgets, QtCore, QtGui
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
from src.utils.time_tracker import TimerState
import os


class FloatingPillWidget(QtWidgets.QWidget):
    """
    A compact floating widget that displays the current task and timer.

    This widget sits on top of other windows and provides quick access to
    basic timer controls while taking minimal screen space.
    """

    def __init__(self, main_window, parent=None):
        """
        Initialize the floating pill widget.

        Args:
            main_window: Reference to the main application window
            parent: Parent widget, if any
        """
        super().__init__(parent)

        # Initialize logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing floating pill widget")

        # Store reference to main window and UI service
        if main_window is None:
            self.logger.critical("Main window reference is None")
            raise ValueError("Main window reference cannot be None")

        self.main_window = main_window
        self.task_manager = main_window.task_manager

        # Explicitly set the parent to the main window to maintain the relationship
        self.setParent(main_window)

        # Ensure UI service is initialized
        if not hasattr(main_window, 'ui_service') or main_window.ui_service is None:
            self.logger.critical("UI service not initialized in main window")
            raise ValueError("UI service must be initialized in main window")

        self.ui_service = main_window.ui_service

        # Log to confirm references
        self.logger.debug(f"Main window reference: {self.main_window}")
        self.logger.debug(f"UI service reference: {self.ui_service}")

        # Set window flags for floating behavior
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )

        # Allow window to be moved with mouse
        self.setMouseTracking(True)
        self.dragging = False
        self.drag_position = None

        # Set size and transparent background
        self.setMinimumWidth(200)
        self.setMaximumHeight(40)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Setup UI components
        self.setup_ui()

        # Add timer for updates
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second

        # Update initial state
        self.update_display()

        self.logger.debug("Floating pill widget initialized")

    def setup_ui(self):
        """
        Set up the user interface components.
        """
        self.logger.debug("Setting up floating pill UI")

        # Main layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Container widget with rounded corners and background
        container = QtWidgets.QWidget(self)
        container.setObjectName("pillContainer")
        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(8, 4, 8, 4)
        container_layout.setSpacing(5)

        # Task name (truncated) or "No Task"
        self.task_label = QtWidgets.QLabel("No Task")
        self.task_label.setStyleSheet("color: white; font-weight: bold;")
        self.task_label.setMinimumWidth(80)
        self.task_label.setMaximumWidth(100)
        container_layout.addWidget(self.task_label)

        # Timer display
        self.timer_label = QtWidgets.QLabel("00:00:00")
        self.timer_label.setStyleSheet("color: white;")
        container_layout.addWidget(self.timer_label)

        # Action buttons
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.setSpacing(2)

        # Start button
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.setMaximumWidth(24)
        self.start_button.setMaximumHeight(24)
        self.start_button.setToolTip("Start New Task")
        self.start_button.clicked.connect(self.safe_start)
        self.button_layout.addWidget(self.start_button)

        # Pause/Resume button
        self.pause_resume_button = QtWidgets.QPushButton()
        self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        self.pause_resume_button.setMaximumWidth(24)
        self.pause_resume_button.setMaximumHeight(24)
        self.pause_resume_button.setToolTip("Pause")
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.button_layout.addWidget(self.pause_resume_button)

        # Stop button
        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.setMaximumWidth(24)
        self.stop_button.setMaximumHeight(24)
        self.stop_button.setToolTip("Stop")
        self.stop_button.clicked.connect(self.main_window.stop_task)
        self.button_layout.addWidget(self.stop_button)

        # Settings/expand button
        self.expand_button = QtWidgets.QPushButton()
        self.expand_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ToolBarVerticalExtensionButton))
        self.expand_button.setMaximumWidth(24)
        self.expand_button.setMaximumHeight(24)
        self.expand_button.setToolTip("Open Main Window")
        self.expand_button.clicked.connect(self.show_main_window)
        self.button_layout.addWidget(self.expand_button)

        container_layout.addLayout(self.button_layout)

        # Add container to main layout
        layout.addWidget(container)

        # Apply stylesheet
        self.setStyleSheet("""
            #pillContainer {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 15px;
            }
            QPushButton {
                background-color: rgba(60, 60, 60, 180);
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 220);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 250);
            }
        """)

        self.logger.debug("Floating pill UI setup complete")

    def update_display(self):
        """
        Update the display with current task and timer information.
        Called by the update timer.
        """
        # Update timer display
        timer_state = self.ui_service.get_timer_state()

        if timer_state == TimerState.STOPPED:
            # Reset timer display when no task is running
            self.timer_label.setText("00:00:00")
        else:
            # Show elapsed time for running or paused tasks
            elapsed_time = self.ui_service.get_elapsed_time_formatted()
            self.timer_label.setText(elapsed_time)

        # Update task name
        task_name = self.ui_service.get_current_task_name()
        if task_name:
            # Truncate if too long
            if len(task_name) > 15:
                self.task_label.setText(task_name[:12] + "...")
            else:
                self.task_label.setText(task_name)
        else:
            self.task_label.setText("No Task")

        # Update button states based on timer state
        timer_state = self.ui_service.get_timer_state()

        if timer_state == TimerState.RUNNING:
            self.start_button.setEnabled(False)
            self.pause_resume_button.setEnabled(True)
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
            self.pause_resume_button.setToolTip("Pause")
            self.stop_button.setEnabled(True)
        elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
            self.start_button.setEnabled(False)
            self.pause_resume_button.setEnabled(True)
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.pause_resume_button.setToolTip("Resume")
            self.stop_button.setEnabled(True)
        else:  # STOPPED
            self.start_button.setEnabled(True)
            self.pause_resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)

        # Have the time tracker check for idle/long pause
        if timer_state == TimerState.RUNNING:
            self.ui_service.time_tracker.check_idle()
        elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
            self.ui_service.time_tracker.check_long_pause()

    def toggle_pause_resume(self):
        """
        Toggle between pause and resume based on current timer state.
        """
        timer_state = self.ui_service.get_timer_state()

        if timer_state == TimerState.RUNNING:
            self.main_window.pause_task()
        else:
            self.main_window.resume_task()

    def show_main_window(self):
        """
        Show the main application window.
        """
        self.logger.debug("Opening main window from pill widget")
        self.main_window.show()
        self.main_window.setWindowState(
            self.main_window.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.main_window.activateWindow()

    def mousePressEvent(self, event):
        """
        Handle mouse press events for dragging.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events for dragging.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.buttons() == QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events for dragging.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """
        Handle mouse double-click events.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.button() == QtCore.Qt.LeftButton:
            # Show main window on double-click
            self.show_main_window()
            event.accept()

    def safe_start(self):
        """Safely handle start button click."""
        try:
            self.logger.debug("Start button clicked in floating pill")

            # Show floating message to indicate what's happening
            QtWidgets.QToolTip.showText(
                self.mapToGlobal(self.start_button.pos()),
                "Creating new task...",
                self
            )

            # Use the task manager directly
            success = self.task_manager.prompt_for_new_task(self.main_window)
            if not success:
                self.logger.warning("Task creation was cancelled or failed")

        except Exception as e:
            self.logger.error(f"Error starting task from pill: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
