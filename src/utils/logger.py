import logging
import os
from datetime import datetime


class AppLogger:
    """
    Handles application logging to keep track of application events and errors.
    """
    # Class variable to track if logger is already configured
    _loggers = {}

    def __init__(self, log_dir, log_level=logging.INFO):
        """
        Initialize the logger with the directory for log files.

        Args:
            log_dir (str): Directory where log files will be stored
            log_level (int): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create a unique log filename based on current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"app_{current_date}.log")

        # Configure logger
        logger_name = "ProductivityTracker"

        # Check if logger already exists to prevent duplicate handlers
        if logger_name in self._loggers:
            self.logger = self._loggers[logger_name]
        else:
            self.logger = logging.getLogger(logger_name)
            self.logger.setLevel(log_level)

            # Only add handler if it doesn't already have handlers
            if not self.logger.handlers:
                # Create file handler for writing to log file
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(log_level)

                # Create formatter for log messages
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)

                # Add the handler to the logger
                self.logger.addHandler(file_handler)

            # Save in class variable to prevent duplicate handlers
            self._loggers[logger_name] = self.logger

    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message):
        """Log an informational message."""
        self.logger.info(message)

    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message):
        """Log an error message."""
        self.logger.error(message)

    def critical(self, message):
        """Log a critical error message."""
        self.logger.critical(message)
