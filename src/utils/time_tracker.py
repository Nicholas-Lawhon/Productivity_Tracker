from src.utils.path_utils import get_project_root
from src.utils.logger import AppLogger
from datetime import datetime
from enum import Enum
import psutil
import time
import os


class TimerState(Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2  # User-initiated pause
    IDLE = 3    # System-detected idle


class PauseReason(Enum):
    USER = 0    # User manually paused
    IDLE = 1    # System detected idle
    SYSTEM = 2  # System event (sleep, shutdown)


class TimeTracker:
    def __init__(self, task_name="", paused_duration_alert=600, idle_threshold=300):
        self.state = TimerState.STOPPED
        self.task_name = task_name
        self.start_time = None
        self.elapsed_time = 0  # In seconds
        self.pause_time = None
        self.last_pause_reason = None
        self.idle_start_time = None
        self.total_idle_time = 0  # In seconds
        self.idle_threshold = idle_threshold  # 5 minutes default idle threshold
        self.paused_duration_alert = paused_duration_alert  # Default alert after 10 minutes of pause

        # Setup logger
        log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)

        # Event Callbacks
        self.on_state_change = None  # Function to call when state changes
        self.on_idle_detected = None  # Function to call when idle is detected
        self.on_long_pause = None  # Function to call when paused for too long

        # Last activity timestamp (for idle detection)
        self.last_activity_time = time.time()

    def start(self, task_name=""):
        """Start the timer with an optional task name."""
        if task_name:
            self.task_name = task_name

        if self.state == TimerState.STOPPED:
            self.start_time = time.time()
            self.elapsed_time = 0  # Reset elapsed time for a new session
            self.state = TimerState.RUNNING
            self.logger.info(f"Timer started for task: '{self.task_name}'")

            # Call state change callback if exists
            if self.on_state_change:
                self.on_state_change(self.state)

            return True
        else:
            self.logger.warning(f"Cannot start timer: Timer already in state {self.state}")
            return False

    def stop(self):
        """Stop the timer and calculate final elapsed time."""
        if self.state != TimerState.STOPPED:
            previous_state = self.state

            # Calculate final elapsed time (if running)
            if self.state == TimerState.RUNNING:
                self.elapsed_time += (time.time() - self.start_time)

            self.state = TimerState.STOPPED

            # Get elapsed time in hours
            hours_elapsed = self.get_elapsed_time(in_hours=True)
            self.logger.info(f"Timer stopped for task: '{self.task_name}'. Total time: {hours_elapsed:.2f} hours")

            # Call state change callback if exists
            if self.on_state_change:
                self.on_state_change(self.state)

            # Get the elapsed time of the session
            return hours_elapsed

        else:
            self.logger.warning(f"Cannot stop timer: Timer already in state {self.state}")
            return 0

    def pause(self, reason=PauseReason.USER):
        """
        Pause the timer with a specified reason.

        Args:
            reason (PauseReason): The reason for pausing (user, idle, system)

        Returns:
            bool: True if successful, False otherwise
        """
        if self.state == TimerState.RUNNING:
            # Record the time of when paused is pressed
            self.pause_time = time.time()

            # Calculate elapsed time up to this pause and add to accumulated time
            self.elapsed_time += (self.pause_time - self.start_time)

            # Update state based on reason
            previous_state = self.state
            if reason == PauseReason.IDLE:
                self.state = TimerState.IDLE
                self.idle_start_time = self.pause_time
            else:
                self.state = TimerState.PAUSED

            self.last_pause_reason = reason
            self.logger.info(f"Timer paused for task: '{self.task_name}'. Reason: {reason.name}")

            # Call callbacks
            if self.on_state_change:
                self.on_state_change(self.state)

            if reason == PauseReason.IDLE and self.on_idle_detected:
                self.on_idle_detected()

            return True
        else:
            self.logger.warning(f"Cannot pause timer: Timer is in state {self.state}")
            return False

    def resume(self):
        """Resume the timer from a paused or idle state."""
        if self.state in [TimerState.PAUSED, TimerState.IDLE]:
            # Store the previous state for logging/calculations
            previous_state = self.state

            if previous_state == TimerState.IDLE and self.idle_start_time:
                # Calculate idle duration and update total_idle_time
                idle_duration = time.time() - self.idle_start_time
                self.total_idle_time += idle_duration
                self.logger.info(f"Resumed after {idle_duration:.1f} seconds of idle time")

            # Reset the start time to now
            self.start_time = time.time()
            self.state = TimerState.RUNNING
            self.logger.info(f"Timer resumed for task: '{self.task_name}' from {previous_state.name} state")

            # Call state change callback if exists
            if self.on_state_change:
                self.on_state_change(self.state)

            return True
        else:
            self.logger.warning(f"Cannot resume timer: Timer is in state {self.state}")
            return False

    def check_idle(self):
        """Check if system is idle and handle appropriately."""
        if self.state == TimerState.RUNNING:
            # Get system idle time in seconds
            idle_time = self._get_system_idle_time()

            # If idle time exceeds threshold, pause the timer
            if idle_time >= self.idle_threshold:
                self.logger.info(f"System idle detected: {idle_time:.1f} seconds")
                # Auto-pause due to idle
                self.pause(reason=PauseReason.IDLE)

                return True

        return False

    def check_long_pause(self):
        """
        Check if timer has been paused for too long and trigger callback if needed.

        Returns:
            bool: True if the pause duration exceeds the alert threshold, False otherwise
        """
        if self.state in [TimerState.PAUSED, TimerState.IDLE] and self.pause_time:
            # Calculate how long the timer has been paused
            current_time = time.time()
            pause_duration = current_time - self.pause_time

            # Check if pause duration exceeds threshold
            if pause_duration >= self.paused_duration_alert:
                # Format pause duration in minutes for logging
                minutes = pause_duration / 60
                self.logger.warning(f"Timer paused for {minutes:.1f} minutes")

                # Call the long pause callback if it exists
                if self.on_long_pause:
                    self.on_long_pause(pause_duration)

                return True

        return False

    def get_elapsed_time(self, in_hours=False):
        """
        Get the current elapsed time.

        Args:
            in_hours (bool): If True, returns time in hours; otherwise, in seconds.

        Returns:
            float: The elapsed time in the requested unit.
        """
        current_elapsed = self.elapsed_time

        # If timer is currently running, add the time since last start
        if self.state == TimerState.RUNNING and self.start_time:
            current_elapsed += (time.time() - self.start_time)

        # Convert to hours if requested
        if in_hours:
            return current_elapsed / 3600  # 3600 seconds in an hour

        return current_elapsed

    def _get_system_idle_time(self):
        """Get the system idle time in seconds using Win32 API."""
        try:
            import win32api
            # GetLastInputInfo returns the number of milliseconds since system startup
            # of the last input event (keyboard/mouse)
            last_input_info = win32api.GetLastInputInfo()
            # GetTickCount returns milliseconds since system startup
            tick_count = win32api.GetTickCount()
            # Calculate idle time in milliseconds, then convert to seconds
            idle_time = (tick_count - last_input_info) / 1000.0
            return idle_time
        except Exception as e:
            self.logger.error(f"Error detecting system idle time: {e}")
            return 0
