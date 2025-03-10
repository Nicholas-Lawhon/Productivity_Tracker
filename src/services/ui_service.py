from src.utils.time_tracker import TimeTracker, TimerState, PauseReason
from src.services.db_service import DatabaseService
from src.services.sheets_service import SheetsService
from src.utils.path_utils import get_project_root
from src.utils.notification_utils import show_notification
from src.utils.logger import AppLogger
import os
import datetime


class UIService:
    """
    Service class that coordinates between UI and backend services.

    This class handles business logic for the UI components, connecting
    the time tracker, database, and sheets services.
    """

    def __init__(self):
        """
        Initialize the UI service and connect to backend services.
        """
        # Get paths
        project_root = get_project_root()
        db_path = os.path.join(project_root, 'data', 'local_db.sqlite')
        log_dir = os.path.join(project_root, 'logs')
        credentials_path = os.path.join(project_root, 'credentials', 'sheets-credentials.json')

        # Initialize logger
        self.logger = AppLogger(log_dir)
        self.logger.info("Initializing UI Service")

        # Initialize services
        self.time_tracker = TimeTracker()
        self.db_service = DatabaseService(db_path, log_dir)
        self.sheets_service = SheetsService(credentials_path, "Productivity Tracker", log_dir)
        self.logger.debug("Backend services initialized")

        # Callback handlers
        self._state_change_callback = None
        self._idle_callback = None
        self._long_pause_callback = None

        # Connect time tracker callbacks
        self.time_tracker.on_state_change = self._on_state_change
        self.time_tracker.on_idle_detected = self._on_idle_detected
        self.time_tracker.on_long_pause = self._on_long_pause
        self.logger.debug("Time tracker callbacks connected")
        self.logger.info("UI Service initialization complete")

    def register_state_change_callback(self, callback):
        """
        Register a callback for timer state changes.

        Args:
            callback: Function to call when state changes
        """
        self.logger.debug("Registering state change callback")
        self._state_change_callback = callback

    def register_idle_callback(self, callback):
        """
        Register a callback for idle detection.

        Args:
            callback: Function to call when idle is detected
        """
        self.logger.debug("Registering idle detection callback")
        self._idle_callback = callback

    def register_long_pause_callback(self, callback):
        """
        Register a callback for long pause detection.

        Args:
            callback: Function to call when timer is paused for too long
        """
        self.logger.debug("Registering long pause callback")
        self._long_pause_callback = callback

    def _on_state_change(self, new_state):
        """Internal handler for state changes."""
        self.logger.debug(f"Time tracker state changed to: {new_state.name}")
        if self._state_change_callback:
            self._state_change_callback(new_state)

    def _on_idle_detected(self):
        """Internal handler for idle detection."""
        self.logger.info("System idle detected")
        show_notification("Idle Detected", "Timer paused due to inactivity.")
        if self._idle_callback:
            self._idle_callback()

    def _on_long_pause(self, duration):
        """Internal handler for long pauses."""
        minutes = int(duration / 60)
        self.logger.warning(f"Timer paused for {minutes} minutes")
        show_notification("Timer Paused", f"Timer has been paused for {minutes} minutes.")
        if self._long_pause_callback:
            self._long_pause_callback(duration)

    def start_task(self, task_name, description=None, categories=None):
        """
        Start tracking a new task.

        Args:
            task_name (str): Name of the task
            description (str, optional): Task description
            categories (list, optional): List of categories/tags for the task

        Returns:
            bool: True if started successfully
        """
        self.logger.info(f"Starting new task: '{task_name}'")

        # Log additional parameters if provided
        if description:
            self.logger.debug(f"Task description: {description}")

        if categories and len(categories) > 0:
            categories_str = ", ".join(categories)
            self.logger.debug(f"Task tags: {categories_str}")

        # Store additional info as properties
        self.current_task_description = description
        self.current_task_categories = categories

        # Start the task
        success = self.time_tracker.start(task_name)

        if success:
            self.logger.info(f"Task '{task_name}' started successfully")
        else:
            self.logger.warning(f"Failed to start task '{task_name}'")

        return success

    def pause_task(self):
        """
        Pause the current task.

        Returns:
            bool: True if paused successfully
        """
        task_name = self.get_current_task_name()
        self.logger.info(f"Pausing task: '{task_name}'")

        success = self.time_tracker.pause(PauseReason.USER)

        if success:
            self.logger.info(f"Task '{task_name}' paused successfully")
        else:
            self.logger.warning(f"Failed to pause task '{task_name}'")

        return success

    def resume_task(self):
        """
        Resume the paused task.

        Returns:
            bool: True if resumed successfully
        """
        task_name = self.get_current_task_name()
        self.logger.info(f"Resuming task: '{task_name}'")

        success = self.time_tracker.resume()

        if success:
            self.logger.info(f"Task '{task_name}' resumed successfully")
        else:
            self.logger.warning(f"Failed to resume task '{task_name}'")

        return success

    def stop_task(self):
        """
        Stop the current task and save to database.

        Returns:
            bool: True if stopped and saved successfully
        """
        task_name = self.get_current_task_name()
        self.logger.info(f"Stopping task: '{task_name}'")

        # Stop the timer and get elapsed time
        hours_elapsed = self.time_tracker.stop()

        if hours_elapsed > 0:
            self.logger.info(f"Task '{task_name}' stopped. Elapsed time: {hours_elapsed:.2f} hours")

            # Get current date
            today = datetime.datetime.now().strftime("%Y-%m-%d")

            categories_str = ""
            if hasattr(self, 'current_task_categories') and self.current_task_categories:
                categories_str = ", ".join(self.current_task_categories)

            # Save to database
            try:
                task_id = self.db_service.add_session_task(
                    date=today,
                    time_elapsed=hours_elapsed,
                    task_name=task_name,
                    description=getattr(self, 'current_task_description', ""),
                    category=categories_str
                )

                if task_id:
                    self.logger.info(f"Task saved to database with ID: {task_id}")
                    return True
                else:
                    self.logger.error("Failed to save task to database - no ID returned")
                    return False

            except Exception as e:
                self.logger.error(f"Error saving task to database: {e}")
                return False
        else:
            self.logger.warning(f"No elapsed time for task '{task_name}' or no task was running")
            return False

    def sync_to_sheets(self):
        """
        Sync unsynced tasks to Google Sheets.

        Returns:
            bool: True if sync was successful
        """
        self.logger.info("Starting sync to Google Sheets")

        try:
            # Get unsynced tasks
            unsynced_tasks = self.db_service.get_unsynced_tasks()

            if not unsynced_tasks:
                self.logger.info("No tasks to sync")
                return True  # Nothing to sync

            self.logger.info(f"Found {len(unsynced_tasks)} tasks to sync")

            # Authenticate sheets service
            self.logger.debug("Authenticating with Google Sheets")
            if not self.sheets_service.authenticate():
                self.logger.error("Failed to authenticate with Google Sheets")
                show_notification("Sync Failed", "Could not connect to Google Sheets.")
                return False

            # Sync each task
            success_count = 0
            for task in unsynced_tasks:
                # Format date as desired (MM/DD/YYYY format)
                date_obj = datetime.datetime.strptime(task['date'], "%Y-%m-%d")
                formatted_date = date_obj.strftime("%m/%d/%Y")
                self.logger.debug(f"Syncing task ID {task['id']}: {task['task_name']}")

                # Format row for Google Sheets
                row_data = [
                    formatted_date,
                    task['Time(hrs)'],
                    task['Task'],
                    task.get('Description', ""),
                    ", ".join(task.get('category', [])) if isinstance(task.get('category'), list) else task.get('category', "")  # Tags
                ]

                # Append to sheet
                self.sheets_service.append_row(row_data)

                # Mark as synced in database
                self.db_service.mark_as_synced(task['id'])
                success_count += 1
                self.logger.debug(f"Task ID {task['id']} synced successfully")

            # Show success notification
            self.logger.info(f"Successfully synced {success_count} tasks to Google Sheets")
            show_notification("Sync Complete", f"Successfully synced {success_count} tasks.")
            return True

        except Exception as e:
            self.logger.error(f"Error syncing tasks to Google Sheets: {e}")
            show_notification("Sync Error", f"Error syncing tasks: {str(e)}")
            return False

    def get_elapsed_time_formatted(self):
        """
        Get the current elapsed time formatted as HH:MM:SS.

        Returns:
            str: Formatted time string
        """
        seconds = int(self.time_tracker.get_elapsed_time())
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def is_timer_running(self):
        """
        Check if the timer is currently running.

        Returns:
            bool: True if the timer is running
        """
        return self.time_tracker.state == TimerState.RUNNING

    def get_unsynced_tasks_count(self):
        """
        Get the count of tasks that haven't been synced to Google Sheets.

        Returns:
            int: Number of unsynced tasks
        """
        try:
            unsynced_tasks = self.db_service.get_unsynced_tasks()
            count = len(unsynced_tasks)
            self.logger.debug(f"Found {count} unsynced tasks")
            return count
        except Exception as e:
            self.logger.error(f"Error getting unsynced tasks count: {e}")
            return 0

    def get_current_task_name(self):
        """
        Get the name of the current task.

        Returns:
            str: Name of the current task, or empty string if no task is running
        """
        if self.time_tracker.state == TimerState.STOPPED:
            return ""
        return self.time_tracker.task_name

    def get_timer_state(self):
        """
        Get the current state of the timer.

        Returns:
            TimerState: Current state of the timer
        """
        return self.time_tracker.state

    def get_task_stats(self):
        """
        Get statistics for the current task session.

        Returns:
            dict: Statistics for the current session including:
                  - elapsed_time (float): Elapsed time in seconds
                  - idle_time (float): Total idle time in seconds
                  - effective_time (float): Elapsed time minus idle time
        """
        elapsed_time = self.time_tracker.get_elapsed_time()
        idle_time = self.time_tracker.total_idle_time
        effective_time = elapsed_time - idle_time

        stats = {
            'elapsed_time': elapsed_time,
            'idle_time': idle_time,
            'effective_time': max(0, effective_time)  # Ensure it's not negative
        }

        self.logger.debug(
            f"Task stats - Elapsed: {elapsed_time:.1f}s, Idle: {idle_time:.1f}s, Effective: {stats['effective_time']:.1f}s")
        return stats
