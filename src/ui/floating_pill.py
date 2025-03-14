from PyQt5 import QtWidgets, QtCore, QtGui
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root
from src.utils.time_tracker import TimerState
import os


class FloatingPillWidget(QtWidgets.QWidget):
    """
    A compact dockable widget that displays the current task and timer.

    This widget can snap to screen edges and provides quick access to
    basic timer controls while taking minimal screen space.
    """

    # Distance in pixels to trigger edge snapping
    SNAP_DISTANCE = 20

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
        self.logger.info("Initializing dockable pill widget")

        # Set a default size before anything else - wider to prevent squishing
        self.setFixedSize(320, 40)

        # Store reference to main window and UI service
        if main_window is None:
            self.logger.critical("Main window reference is None")
            raise ValueError("Main window reference cannot be None")

        self.main_window = main_window
        self.task_manager = main_window.task_manager

        # Store the parent temporarily but we'll make this a top-level window
        self._parent = parent

        # Ensure UI service is initialized
        if not hasattr(main_window, 'ui_service') or main_window.ui_service is None:
            self.logger.critical("UI service not initialized in main window")
            raise ValueError("UI service must be initialized in main window")

        self.ui_service = main_window.ui_service

        # Log to confirm references
        self.logger.debug(f"Main window reference: {self.main_window}")
        self.logger.debug(f"UI service reference: {self.ui_service}")

        # Set window flags for floating behavior with proper layering
        self.setWindowFlags(
            QtCore.Qt.Window |  # Make it a window
            QtCore.Qt.FramelessWindowHint |  # No window frame
            QtCore.Qt.WindowStaysOnTopHint |  # Stay on top of other windows
            QtCore.Qt.Tool  # Tool window (doesn't show in taskbar)
        )

        # Set window attributes for proper behavior
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)  # Transparent background
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)  # Don't steal focus when shown

        # Setup for mouse dragging
        self.setMouseTracking(True)
        self.dragging = False
        self.drag_position = None

        # Edge docking properties
        self.docked_edge = None  # 'top', 'right', 'bottom', 'left', or None
        self.screen_geometry = None
        self.update_screen_geometry()

        # Expanded/collapsed state
        self.is_collapsed = False
        self.expanded_size = QtCore.QSize(200, 40)  # Default expanded size
        self.collapsed_size = QtCore.QSize(40, 40)  # Default collapsed size

        # Set size
        self.setMinimumWidth(200)
        self.setMaximumHeight(40)

        # Animation for sliding
        self.animation = QtCore.QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)  # 200ms animation

        # Setup UI components
        self.setup_ui()

        # Load saved position
        self.load_position()

        # Add timer for updates
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second

        # Update initial state
        self.update_display()

        # Create a timer to hide when mouse is not over
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.check_mouse_for_autohide)

        # Auto-hide after 3 seconds of inactivity
        self.auto_hide_delay = 3000  # 3 seconds

        self.logger.debug("Dockable pill widget initialized")

    def setup_ui(self):
        """
        Set up the user interface components.
        """
        self.logger.debug("Setting up dockable pill UI")

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

        # Pin button to toggle auto-hide
        self.pin_button = QtWidgets.QPushButton()
        self.pin_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        self.pin_button.setMaximumWidth(24)
        self.pin_button.setMaximumHeight(24)
        self.pin_button.setToolTip("Pin (Disable Auto-hide)")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(False)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.button_layout.addWidget(self.pin_button)

        container_layout.addLayout(self.button_layout)

        # Add container to main layout
        layout.addWidget(container)

        # Apply stylesheet
        self.setStyleSheet("""
            #pillContainer {
                background-color: rgba(60, 80, 120, 240);
                border-radius: 15px;
                border: 1px solid rgba(100, 150, 200, 200);
            }
            QPushButton {
                background-color: rgba(80, 100, 140, 200);
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(100, 120, 160, 240);
            }
            QPushButton:pressed {
                background-color: rgba(120, 140, 180, 250);
            }
            QPushButton:checked {
                background-color: rgba(100, 180, 120, 250);
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)

        self.logger.debug("Dockable pill UI setup complete")

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

            # If collapsed, update the container color to green
            if self.is_collapsed:
                self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                    "background-color: rgba(60, 120, 80, 240); border-radius: 15px; border: 1px solid rgba(100, 200, 120, 200);"
                )

        elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
            self.start_button.setEnabled(False)
            self.pause_resume_button.setEnabled(True)
            self.pause_resume_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.pause_resume_button.setToolTip("Resume")
            self.stop_button.setEnabled(True)

            # If collapsed, update the container color to orange
            if self.is_collapsed:
                self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                    "background-color: rgba(180, 120, 60, 240); border-radius: 15px; border: 1px solid rgba(220, 180, 100, 200);"
                )

        else:  # STOPPED
            self.start_button.setEnabled(True)
            self.pause_resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)

            # If collapsed, reset to default blue
            if self.is_collapsed:
                self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                    "background-color: rgba(60, 80, 120, 240); border-radius: 15px; border: 1px solid rgba(100, 150, 200, 200);"
                )

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

    def update_screen_geometry(self):
        """Update stored screen geometry."""
        screen = QtWidgets.QApplication.primaryScreen()
        self.screen_geometry = screen.availableGeometry()
        self.logger.debug(f"Screen geometry updated: {self.screen_geometry.width()}x{self.screen_geometry.height()}")

    def snap_to_edge(self, pos):
        """Determine if position should snap to an edge and return the snapped position."""
        self.update_screen_geometry()

        # Get the screen geometry
        screen_geom = self.screen_geometry

        # Widget dimensions
        widget_width = self.width()
        widget_height = self.height()

        # Initialize snapped position with original position
        snapped_pos = QtCore.QPoint(pos)
        self.docked_edge = None

        # Check for left edge snap
        if pos.x() < self.SNAP_DISTANCE:
            snapped_pos.setX(0)
            self.docked_edge = 'left'

        # Check for right edge snap
        elif (screen_geom.width() - (pos.x() + widget_width)) < self.SNAP_DISTANCE:
            snapped_pos.setX(screen_geom.width() - widget_width)
            self.docked_edge = 'right'

        # Check for top edge snap
        if pos.y() < self.SNAP_DISTANCE:
            snapped_pos.setY(0)
            self.docked_edge = 'top'

        # Check for bottom edge snap
        elif (screen_geom.height() - (pos.y() + widget_height)) < self.SNAP_DISTANCE:
            snapped_pos.setY(screen_geom.height() - widget_height)
            self.docked_edge = 'bottom'

        # Check for corner snaps and prioritize them
        if pos.x() < self.SNAP_DISTANCE and pos.y() < self.SNAP_DISTANCE:
            self.docked_edge = 'top-left'
        elif pos.x() < self.SNAP_DISTANCE and (screen_geom.height() - (pos.y() + widget_height)) < self.SNAP_DISTANCE:
            self.docked_edge = 'bottom-left'
        elif (screen_geom.width() - (pos.x() + widget_width)) < self.SNAP_DISTANCE and pos.y() < self.SNAP_DISTANCE:
            self.docked_edge = 'top-right'
        elif (screen_geom.width() - (pos.x() + widget_width)) < self.SNAP_DISTANCE and (
                screen_geom.height() - (pos.y() + widget_height)) < self.SNAP_DISTANCE:
            self.docked_edge = 'bottom-right'

        if self.docked_edge:
            self.logger.debug(f"Snapped to edge: {self.docked_edge}")

        return snapped_pos

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
        Handle mouse move events for dragging - restricts movement past snap points.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.buttons() == QtCore.Qt.LeftButton and self.dragging:
            # Get the new global position based on drag
            new_pos = event.globalPos() - self.drag_position

            # Get all screens for multi-monitor support
            screens = QtWidgets.QApplication.screens()

            # Widget dimensions
            widget_width = self.width()
            widget_height = self.height()

            # Variables to track snap
            was_snapped = False

            # Check each screen for potential edge snapping
            for screen in screens:
                screen_geom = screen.availableGeometry()

                # Check if we're near screen edges - using a larger detection area
                detect_distance = self.SNAP_DISTANCE * 3  # Larger detection area

                # Check left edge
                if abs(new_pos.x() - screen_geom.left()) < detect_distance:
                    was_snapped = True
                    self.docked_edge = 'left'
                    new_pos.setX(screen_geom.left())
                    break

                # Check right edge
                if abs((screen_geom.right() - widget_width) - new_pos.x()) < detect_distance:
                    was_snapped = True
                    self.docked_edge = 'right'
                    new_pos.setX(screen_geom.right() - widget_width)
                    break

                # Check top edge
                if abs(new_pos.y() - screen_geom.top()) < detect_distance:
                    was_snapped = True
                    self.docked_edge = 'top'
                    new_pos.setY(screen_geom.top())
                    break

                # Check bottom edge
                if abs((screen_geom.bottom() - widget_height) - new_pos.y()) < detect_distance:
                    was_snapped = True
                    self.docked_edge = 'bottom'
                    new_pos.setY(screen_geom.bottom() - widget_height)
                    break

            # If not snapped to any edge, clear the docked edge flag
            if not was_snapped:
                self.docked_edge = None

            # Move to the new position
            self.move(new_pos)
            event.accept()

            # If snapped, immediately check if we should collapse the widget
            if was_snapped and not self.pin_button.isChecked():
                # Only collapse if mouse is outside the widget
                global_pos = QtGui.QCursor.pos()
                local_pos = self.mapFromGlobal(global_pos)
                if not self.rect().contains(local_pos):
                    # Start a short timer to collapse after a brief delay
                    QtCore.QTimer.singleShot(300, self.check_mouse_for_autohide)

        # Reset the auto-hide timer when mouse moves over the widget
        if self.rect().contains(event.pos()) and not self.pin_button.isChecked():
            self.restart_hide_timer()

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events for dragging.

        Args:
            event (QMouseEvent): The mouse event
        """
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False

            # Save position when dragging ends
            self.save_position()

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

    def enterEvent(self, event):
        """Handle mouse entering the widget."""
        # If the widget is collapsed, expand it immediately
        if self.is_collapsed:
            self.expand_widget()

        # Cancel any pending hide timer
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leaving the widget."""
        # Start the timer to check if we should hide
        if not self.pin_button.isChecked():
            self.restart_hide_timer()

        super().leaveEvent(event)

    def restart_hide_timer(self):
        """Restart the timer for auto-hiding."""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
            self.hide_timer.start(self.auto_hide_delay)

    def check_mouse_for_autohide(self):
        """Check if mouse is still outside the widget and hide if appropriate."""
        # Get global mouse position
        global_pos = QtGui.QCursor.pos()

        # Convert to local position
        local_pos = self.mapFromGlobal(global_pos)

        # Check if mouse is outside the widget
        if not self.rect().contains(local_pos) and not self.pin_button.isChecked():
            # Collapse the widget if it's docked
            if self.docked_edge:
                self.collapse_widget()

    def collapse_widget(self):
        """Collapse the widget to a smaller size based on the docked edge."""
        if not self.docked_edge or self.is_collapsed:
            return

        self.is_collapsed = True

        # Store current geometry for animation
        current_geom = self.geometry()
        target_geom = QtCore.QRect(current_geom)

        # Get timer state and info
        timer_state = self.ui_service.get_timer_state()
        task_name = self.ui_service.get_current_task_name() or "No Task"
        elapsed_time = self.ui_service.get_elapsed_time_formatted()

        # Different collapse behaviors based on edge
        if self.docked_edge == 'left':
            # Left edge: Just show timer, mostly hidden
            collapsed_width = 90  # Width to show timer
            target_geom.setWidth(collapsed_width)
            # Special handling for left edge - hide most of it but ensure timer is visible
            target_geom.moveLeft(current_geom.left() - (collapsed_width - 70))  # Keep 70px visible

            # Hide task name for left/right edges
            self.task_label.setVisible(False)
            self.timer_label.setVisible(True)

            # Update timer display
            if timer_state == TimerState.STOPPED:
                self.timer_label.setText("00:00:00")
            else:
                self.timer_label.setText(elapsed_time)

        elif self.docked_edge == 'right':
            # Right edge: Just show timer, mostly hidden
            collapsed_width = 90  # Width to show timer
            target_geom.setWidth(collapsed_width)
            target_geom.moveLeft(current_geom.right() - 70)  # Keep 70px visible

            # Hide task name for left/right edges
            self.task_label.setVisible(False)
            self.timer_label.setVisible(True)

            # Update timer display
            if timer_state == TimerState.STOPPED:
                self.timer_label.setText("00:00:00")
            else:
                self.timer_label.setText(elapsed_time)

        elif self.docked_edge in ['top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right']:
            # For top/bottom edges: show timer and task name in horizontal layout
            collapsed_width = 200  # Width to display "HH:MM:SS + Task Name"
            target_geom.setWidth(collapsed_width)

            # Update display with timer and task
            if timer_state == TimerState.STOPPED:
                self.timer_label.setText("00:00:00")
                self.task_label.setText("No Task")
            else:
                self.timer_label.setText(elapsed_time)
                # Show truncated task name
                if len(task_name) > 12:
                    self.task_label.setText(task_name[:10] + "...")
                else:
                    self.task_label.setText(task_name)

            # Keep task name visible when docked to top/bottom
            self.task_label.setVisible(True)
            self.timer_label.setVisible(True)

        # Adjust height regardless of docking edge
        target_geom.setHeight(self.collapsed_size.height())

        # Special adjustments for corners to ensure timer visibility
        if 'top' in self.docked_edge and 'left' in self.docked_edge:
            target_geom.moveLeft(current_geom.left() - (collapsed_width - 70))
            # If it's a left corner, only show timer
            self.task_label.setVisible(False)
        elif 'bottom' in self.docked_edge and 'left' in self.docked_edge:
            target_geom.moveLeft(current_geom.left() - (collapsed_width - 70))
            # If it's a left corner, only show timer
            self.task_label.setVisible(False)

        # Start animation
        self.animation.setStartValue(current_geom)
        self.animation.setEndValue(target_geom)
        self.animation.start()

        # Hide buttons in collapsed state
        for btn in [self.start_button, self.pause_resume_button, self.stop_button, self.pin_button, self.expand_button]:
            btn.setVisible(False)

        # Make absolutely sure timer is visible and properly positioned
        self.timer_label.setVisible(True)
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setMinimumWidth(65)  # Ensure timer label is wide enough to show HH:MM:SS

        # Update colors based on timer state
        if timer_state == TimerState.RUNNING:
            # Green for running
            self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                "background-color: rgba(60, 120, 80, 240); border-radius: 15px; border: 1px solid rgba(100, 200, 120, 200);")
        elif timer_state in [TimerState.PAUSED, TimerState.IDLE]:
            # Orange/yellow for paused/idle
            self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                "background-color: rgba(180, 120, 60, 240); border-radius: 15px; border: 1px solid rgba(220, 180, 100, 200);")
        else:
            # Blue for stopped (default)
            self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet(
                "background-color: rgba(60, 80, 120, 240); border-radius: 15px; border: 1px solid rgba(100, 150, 200, 200);")

    def expand_widget(self):
        """Expand the widget to its full size."""
        if not self.is_collapsed:
            return

        self.is_collapsed = False

        # Store current geometry for animation
        current_geom = self.geometry()
        target_geom = QtCore.QRect(current_geom)

        # Set target size
        target_geom.setWidth(self.expanded_size.width())
        target_geom.setHeight(self.expanded_size.height())

        # Adjust position based on edge to keep the widget in the visible area
        if self.docked_edge == 'left':
            # When expanding from left edge, move it back into view
            target_geom.moveLeft(0)  # Align with screen edge
        elif self.docked_edge == 'right':
            # For right edge, align with screen edge
            target_geom.moveLeft(current_geom.right() - self.expanded_size.width())
        elif self.docked_edge in ['top-left', 'bottom-left']:
            # Corner cases with left edge
            target_geom.moveLeft(0)
        elif self.docked_edge in ['top-right', 'bottom-right']:
            # Corner cases with right edge
            target_geom.moveLeft(current_geom.right() - self.expanded_size.width())

        if self.docked_edge in ['bottom', 'bottom-left', 'bottom-right']:
            target_geom.moveTop(current_geom.bottom() - self.expanded_size.height())

        # Start animation
        self.animation.setStartValue(current_geom)
        self.animation.setEndValue(target_geom)
        self.animation.start()

        # Show all elements
        self.task_label.setVisible(True)
        self.timer_label.setVisible(True)

        # Show all buttons
        for btn in [self.start_button, self.pause_resume_button, self.stop_button, self.pin_button, self.expand_button]:
            btn.setVisible(True)

        # Update button states based on timer state
        self.update_display()

        # Reset container style
        self.findChild(QtWidgets.QWidget, "pillContainer").setStyleSheet("")

        # Restart hide timer if not pinned
        if not self.pin_button.isChecked():
            self.restart_hide_timer()

    def toggle_pin(self, checked):
        """Toggle the pinned state (auto-hide disabled when pinned)."""
        if checked:
            # Pin is on, cancel hide timer and expand if collapsed
            self.hide_timer.stop()
            if self.is_collapsed:
                self.expand_widget()
            self.pin_button.setToolTip("Unpin (Enable Auto-hide)")
        else:
            # Pin is off, restart hide timer
            self.restart_hide_timer()
            self.pin_button.setToolTip("Pin (Disable Auto-hide)")

        self.save_position()  # Save the pinned state

    def save_position(self):
        """Save the current position and state to settings."""
        try:
            settings = QtCore.QSettings("ProductivityTracker", "FloatingPill")
            settings.setValue("geometry", self.geometry())
            settings.setValue("docked_edge", self.docked_edge)
            settings.setValue("is_pinned", self.pin_button.isChecked())
            self.logger.debug(
                f"Saved position: {self.geometry()}, edge: {self.docked_edge}, pinned: {self.pin_button.isChecked()}")
        except Exception as e:
            self.logger.error(f"Error saving position: {e}")

    def load_position(self):
        """Load the saved position and state from settings."""
        try:
            settings = QtCore.QSettings("ProductivityTracker", "FloatingPill")

            # Ensure initial size is appropriate - wider to prevent squishing
            self.resize(320, 40)
            self.expanded_size = QtCore.QSize(320, 40)
            self.collapsed_size = QtCore.QSize(90, 40)  # smaller collapsed size, just for timer

            # Load and apply geometry if it exists
            geometry = settings.value("geometry")
            if geometry:
                self.setGeometry(geometry)
                self.logger.debug(f"Loaded geometry: {geometry}")

                # Verify the loaded position is visible on screen
                if not self.is_position_visible():
                    self.logger.warning("Saved position is off-screen, resetting to default")
                    self.reset_to_default_position()
            else:
                # No saved position, use default
                self.reset_to_default_position()

            # Load docked edge
            self.docked_edge = settings.value("docked_edge")
            self.logger.debug(f"Loaded docked edge: {self.docked_edge}")

            # Load pinned state
            is_pinned = settings.value("is_pinned", False, type=bool)
            self.pin_button.setChecked(is_pinned)
            self.logger.debug(f"Loaded pinned state: {is_pinned}")

            if not is_pinned:
                # Start auto-hide timer
                self.restart_hide_timer()
        except Exception as e:
            self.logger.error(f"Error loading position: {e}")
            self.reset_to_default_position()

    def reset_to_default_position(self):
        """Reset to a default visible position (center-top of screen)."""
        screen_geom = self.screen_geometry
        # Position at the top center of the screen
        self.move((screen_geom.width() - self.width()) // 2, 40)
        self.logger.debug("Using default position (top center)")

    def is_position_visible(self):
        """Check if the current position is visible on any screen."""
        # Get all screens
        screens = QtWidgets.QApplication.screens()
        widget_rect = self.frameGeometry()

        # Check if at least part of the widget is visible on any screen
        for screen in screens:
            screen_geom = screen.availableGeometry()
            if widget_rect.intersects(screen_geom):
                return True

        return False

    def safe_start(self):
        """Safely handle start button click with a simple, reliable approach."""
        try:
            self.logger.debug("Start button clicked in floating pill")

            # Show the main window and use its task creation function
            # This is the simplest, most reliable approach
            self.main_window.show()
            self.main_window.setWindowState(
                self.main_window.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            self.main_window.activateWindow()

            # Use a short timer to start task dialog after window is fully activated
            QtCore.QTimer.singleShot(100, self.main_window.start_task_dialog)

        except Exception as e:
            self.logger.error(f"Error in safe_start: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)

        # When shown, make sure to update the expanded size
        if not self.is_collapsed:
            self.expanded_size = self.size()

        # Restart hide timer if not pinned
        if not self.pin_button.isChecked():
            self.restart_hide_timer()

    def get_proper_parent(self):
        """Return the main window as the parent for dialogs."""
        return self.main_window
