from src.utils.logger import AppLogger
import sqlite3
import platform
import os


class DatabaseService:
    def __init__(self, db_path, log_dir=None):
        """Initializes the database service with the path to the database."""
        # Add safety check for db_path
        if db_path is None:
            from src.utils.path_utils import get_project_root
            project_root = get_project_root()
            db_path = os.path.join(project_root, 'data', 'local_db.sqlite')
            print(f"Warning: db_path was None, using: {db_path}")

        self.db_path = db_path

        # Add safety check for log_dir
        if log_dir is None:
            from src.utils.path_utils import get_project_root
            project_root = get_project_root()
            log_dir = os.path.join(project_root, 'logs')
            print(f"Warning: log_dir was None, using: {log_dir}")

        # Make sure DB directory exists
        db_dir = os.path.dirname(db_path)
        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"Ensured database directory exists: {db_dir}")
        except Exception as e:
            print(f"Error with database directory: {e}")

        # Make sure log directory exists
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"Ensured log directory exists: {log_dir}")
        except Exception as e:
            print(f"Error with log directory: {e}")

        # Initialize logger with extra error handling
        try:
            self.logger = AppLogger(log_dir)
            self.logger.info("DatabaseService initialized")
            self.logger.info(f"Database path: {db_path}")
            self.logger.info(f"Log directory: {log_dir}")
        except Exception as e:
            print(f"Error initializing logger: {e}")
            # Create a basic logger or use print statements
            self.logger = SimpleLogger()

        try:
            self._initialize_database()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self.logger.warning("Primary database initialization failed due to lock, trying fallback")
                self._initialize_database_fallback()
            else:
                raise

    def _ensure_directory_exists(self):
        """Make sure the directory with the database file exists."""
        try:
            db_dir = os.path.dirname(self.db_path)
            print(f"Ensuring directory exists: {db_dir}")

            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Created directory: {db_dir}")
            else:
                print(f"Directory already exists: {db_dir}")

            # Test if directory is writable
            test_file = os.path.join(db_dir, "write_test.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("Test")
                os.remove(test_file)
                print(f"Directory {db_dir} is writable")
            except Exception as e:
                print(f"Directory {db_dir} is NOT writable: {e}")

        except Exception as e:
            print(f"Error ensuring directory exists: {e}")
            import traceback
            print(traceback.format_exc())

    def _initialize_database(self):
        """Create the session_tasks table if it doesn't exist."""
        self.logger.info("Initializing database")
        self.logger.info(f"Database path: {self.db_path}")

        # Check if database is locked
        if self._is_database_locked():
            self.logger.warning("Database appears to be locked by another process")

            # Try to recover from previous crash by removing journal files
            journal_path = self.db_path + "-journal"
            if os.path.exists(journal_path):
                try:
                    os.remove(journal_path)
                    self.logger.info("Removed stale journal file")
                except OSError as e:
                    self.logger.error(f"Could not remove journal file: {e}")

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            conn = None
            try:
                # Ensure directory exists
                db_dir = os.path.dirname(self.db_path)
                if not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                    self.logger.info(f"Created directory: {db_dir}")
                else:
                    self.logger.info(f"Directory already exists: {db_dir}")

                # Connect with timeout
                conn = sqlite3.connect(self.db_path, timeout=30)
                cursor = conn.cursor()

                try:
                    # Set journal mode to WAL for better concurrency
                    cursor.execute("PRAGMA journal_mode=WAL")

                    # Set busy timeout
                    cursor.execute("PRAGMA busy_timeout=5000")
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"Could not set PRAGMA options: {e}")
                    # Continue anyway - table creation is more important

                # Creates the database table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hours REAL NOT NULL,
                    task TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    synced_to_sheets INTEGER DEFAULT 0
                )
                ''')

                conn.commit()
                self.logger.info("Database initialized successfully")

                # Verify table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_tasks'")
                table_exists = cursor.fetchone()
                self.logger.info(f"Session tasks table exists: {table_exists is not None}")

                # Success, no need to retry
                break

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    self.logger.warning(f"Database is locked, retrying ({retry_count}/{max_retries})...")
                    import time
                    time.sleep(2)  # Wait longer between retries
                else:
                    self.logger.critical(f"Failed to initialize database: {e}")
                    import traceback
                    self.logger.critical(traceback.format_exc())
                    raise
            except Exception as e:
                self.logger.critical(f"Failed to initialize database: {e}")
                import traceback
                self.logger.critical(traceback.format_exc())
                raise
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def add_session_task(self, date, hours, task, description="", tags=""):
        """
        Add a new task session to the database.

        Args:
            date (str): The date of the task (YYYY-MM-DD format)
            hours (float): Duration of the task in hours
            task (str): Name or description of the task
            description (str, optional): Additional details about the task
            tags (str, optional): Categories or tags for the task

        Returns:
            int: The ID of the newly inserted record
        """
        self.logger.info(f"Adding new session task: {task} on {date} ({hours} hours)")
        conn = None
        retries = 5

        while retries > 0:
            try:
                # Connect to the database with timeout
                conn = sqlite3.connect(self.db_path, timeout=10)
                cursor = conn.cursor()

                # Insert the new session task
                # Note: We don't need to specify synced_to_sheets as it defaults to 0
                cursor.execute('''
                INSERT INTO session_tasks (date, hours, task, description, tags)
                VALUES (?, ?, ?, ?, ?)
                ''', (date, hours, task, description, tags))

                # Get the ID of the inserted row
                last_row_id = cursor.lastrowid

                # Save changes and close connection
                conn.commit()

                self.logger.debug(f"Successfully added task with ID: {last_row_id}")
                return last_row_id

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retries > 1:
                    retries -= 1
                    import time
                    time.sleep(0.5)  # Wait half a second before retry
                    self.logger.warning(f"Database locked, retrying... ({retries} attempts left)")
                else:
                    self.logger.error(f"Failed to add session task: {e}")
                    if conn:
                        conn.rollback()  # Rollback any changes if error occurs
                    raise
            except Exception as e:
                self.logger.error(f"Failed to add session task: {e}")
                if conn:
                    conn.rollback()  # Rollback any changes if error occurs
                raise
            finally:
                if conn:
                    conn.close()

        # If we get here, all retries failed
        self.logger.error("All retries failed when adding session task")
        return None

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
            SELECT id, date, hours, task, description, tags
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
            SELECT id, date, hours, task, description, tags, synced_to_sheets
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

    def _is_database_locked(self):
        """Check if the database is currently locked by another process."""
        print(f"Checking if database is locked: {self.db_path}")

        # Check if the database file exists
        if not os.path.exists(self.db_path):
            print(f"Database file does not exist: {self.db_path}")
            return False

        # Check if the journal file exists (indicating unfinished transaction)
        journal_path = self.db_path + "-journal"
        wal_path = self.db_path + "-wal"

        journal_exists = os.path.exists(journal_path)
        wal_exists = os.path.exists(wal_path)

        print(f"Lock indicators: journal={journal_exists}, wal={wal_exists}")

        if journal_exists or wal_exists:
            return True

        # Try a test connection
        try:
            conn = sqlite3.connect(self.db_path, timeout=1)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            print("Database connection test successful")
            return False
        except sqlite3.OperationalError as e:
            print(f"Database appears to be locked: {e}")
            return True

    def _initialize_database_fallback(self):
        """Fallback method to initialize database without WAL mode."""
        self.logger.warning("Attempting database initialization without WAL mode")
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=20)
            cursor = conn.cursor()

            # Create table without changing journal mode
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                hours REAL NOT NULL,
                task TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                synced_to_sheets INTEGER DEFAULT 0
            )
            ''')

            conn.commit()
            self.logger.info("Database initialized successfully with fallback method")
            return True
        except Exception as e:
            self.logger.critical(f"Even fallback database initialization failed: {e}")
            raise
        finally:
            if conn:
                conn.close()


class SimpleLogger:
    def info(self, message):
        print(f"INFO: {message}")

    def debug(self, message):
        print(f"DEBUG: {message}")

    def warning(self, message):
        print(f"WARNING: {message}")

    def error(self, message):
        print(f"ERROR: {message}")

    def critical(self, message):
        print(f"CRITICAL: {message}")
