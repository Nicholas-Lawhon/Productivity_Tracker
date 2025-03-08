from src.services.sheets_service import SheetsService
from src.utils.path_utils import get_project_root
import os


def main():
    # Use path_utils to get project root
    project_root = get_project_root()

    # Create the full path to the credentials file
    CREDENTIALS_PATH = os.path.join(project_root, 'credentials', 'sheets-credentials.json')
    SPREADSHEET_NAME = 'Productivity Tracker'

    sheets_service = SheetsService(CREDENTIALS_PATH, SPREADSHEET_NAME)

    if sheets_service.test_connection():
        print("Connection successful!")

        # Test getting data
        records = sheets_service.get_all_records()
        print(f"Found {len(records)} records")

        # Uncomment to test adding a row
        # sheets_service.append_row(["2023-11-06", 0.5, "Testing API", "Testing the gspread connection", "Development"])
    else:
        print("Failed to connect to Google Sheets")


if __name__ == "__main__":
    main()
