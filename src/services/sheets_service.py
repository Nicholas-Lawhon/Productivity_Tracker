import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from src.utils.logger import AppLogger
from src.utils.path_utils import get_project_root


class SheetsService:
    def __init__(self, credentials_path, spreadsheet_name, log_dir=None):
        self.scope = ['https://spreadsheets.google.com/feeds',
                      'https://www.googleapis.com/auth/drive']
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None

        # Initialize logger
        if log_dir is None:
            log_dir = os.path.join(get_project_root(), 'logs')
        self.logger = AppLogger(log_dir)
        self.logger.info(f"SheetsService initialized for spreadsheet: {spreadsheet_name}")

    def authenticate(self):
        try:
            self.logger.info("Authenticating with Google Sheets API")
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, self.scope)
            self.client = gspread.authorize(credentials)
            self.sheet = self.client.open(self.spreadsheet_name).sheet1
            self.logger.info("Authentication successful")
            return True
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def test_connection(self):
        if self.authenticate():
            self.logger.info(f"Successfully connected to: {self.spreadsheet_name}")
            return True
        self.logger.warning("Connection test failed")
        return False

    def get_all_records(self):
        try:
            self.logger.info("Getting all records from spreadsheet")
            if not self.sheet:
                self.authenticate()

            # Specify the expected headers based on your sheet structure
            expected_headers = ['Date', 'Time(hrs)', 'Task', 'Description', 'Tags']

            records = self.sheet.get_all_records(expected_headers=expected_headers)
            self.logger.debug(f"Retrieved {len(records)} records from spreadsheet")
            return records
        except Exception as e:
            self.logger.error(f"Error getting records: {e}")
            raise

    def append_row(self, row_data):
        try:
            self.logger.info(f"Appending row to spreadsheet: {row_data}")
            if not self.sheet:
                self.authenticate()
            result = self.sheet.append_row(row_data)
            self.logger.debug("Row successfully appended")
            return result
        except Exception as e:
            self.logger.error(f"Error appending row: {e}")
            raise
