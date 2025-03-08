from src.utils.logger import AppLogger
import sqlite3
import os


class DatabaseService:
    def __init__(self, db_path, log_dir='logs'):
        """Initializes the database service with the path to the database."""
        self.db_path = db_path
        # Initialize logger
        self.logger = AppLogger(log_dir)
        self.logger.info("DatabaseService initialized")
        self._ensure_directory_exists()
        self._initialize_database()

    def _ensure_directory_exists(self):
        """Make sure the directory with the database file exists."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.logger.debug(f"Ensured directory exists for database at: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to create directory for database: {e}")
            raise

    def _initialize_database(self):
        """Create the session_tasks table if it doesn't exist."""
        self.logger.info("Initializing database")
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Creates the database table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time_elapsed REAL NOT NULL,
                task_name TEXT NOT NULL,
                synced_to_sheets INTEGER DEFAULT 0
            )
            ''')

            conn.commit()  # Save the changes
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.critical(f"Failed to initialize database: {e}")
            raise
        finally:
            if conn:
                conn.close()   # Close the connection

    def add_session_task(self, date, time_elapsed, task_name):
        """
        Add a new task session to the database.

        Args:
            date (str): The date of the task (YYYY-MM-DD format)
            time_elapsed (float): Duration of the task in hours
            task_name (str): Name or description of the task

        Returns:
            int: The ID of the newly inserted record
        """
        self.logger.info(f"Adding new session task: {task_name} on {date} ({time_elapsed} hours)")
        conn = None
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert the new session task
            # Note: We don't need to specify synced_to_sheets as it defaults to 0
            cursor.execute('''
            INSERT INTO session_tasks (date, time_elapsed, task_name)
            VALUES (?, ?, ?)
            ''', (date, time_elapsed, task_name))

            # Get the ID of the inserted row
            last_row_id = cursor.lastrowid

            # Save changes and close connection
            conn.commit()

            self.logger.debug(f"Successfully added task with ID: {last_row_id}")
            return last_row_id
        except Exception as e:
            self.logger.error(f"Failed to add session task: {e}")
            if conn:
                conn.rollback()  # Rollback any changes if error occurs
            raise
        finally:
            if conn:
                conn.close()

    def get_unsynced_tasks(self):
        """
        Retrieve all session tasks that haven't been synced to Google Sheets.

        Returns:
            list: List of dictionaries containing unsynced task sessions
        """
        self.logger.info("Retrieving unsynced tasks")
        conn = None
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            # This tells SQLite to return rows as dictionaries
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Select all unsynced records
            cursor.execute('''
            SELECT id, date, time_elapsed, task_name
            FROM session_tasks
            WHERE synced_to_sheets = 0
            ''')

            # Fetch all results
            rows = cursor.fetchall()

            # Convert rows to dictionaries
            results = [dict(row) for row in rows]

            self.logger.debug(f"Found {len(results)} unsynced tasks")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving unsynced tasks: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def mark_as_synced(self, task_id):
        """
        Mark a session task as synced to Google Sheets.

        Args:
            task_id (int): The ID of the task to mark as synced

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info(f"Marking task ID {task_id} as synced")
        conn = None
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update the sync status
            cursor.execute('''
            UPDATE session_tasks
            SET synced_to_sheets = 1
            WHERE id = ?
            ''', (task_id,))

            # Check if any rows were affected
            rows_affected = cursor.rowcount

            # Save changes
            conn.commit()

            if rows_affected > 0:
                self.logger.debug(f"Successfully marked task ID {task_id} as synced")
            else:
                self.logger.warning(f"No task with ID {task_id} found to mark as synced")

            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Error marking task as synced: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_all_tasks(self):
        """
        Retrieve all task sessions.

        Returns:
            list: List of dictionaries containing all task sessions
        """
        self.logger.info("Retrieving all tasks")
        conn = None
        try:
            # Connect to the database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Select all records
            cursor.execute('''
            SELECT id, date, time_elapsed, task_name, synced_to_sheets
            FROM session_tasks
            ORDER BY date DESC
            ''')

            # Fetch all records
            rows = cursor.fetchall()

            # Convert rows to dictionaries
            results = [dict(row) for row in rows]

            self.logger.debug(f"Retrieved {len(results)} tasks")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving all tasks: {e}")
            raise
        finally:
            if conn:
                conn.close()
