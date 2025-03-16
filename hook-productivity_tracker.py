
# PyInstaller hook to include all necessary modules
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Include all submodules from your project
hiddenimports = collect_submodules('src')

# Add specific imports that might be missed
hiddenimports.extend([
    'sqlite3',
    'win32gui',
    'win32con',
    'win10toast',
    'gspread',
    'oauth2client',
    'oauth2client.service_account',
    'psutil'
])

# Include data files
datas = collect_data_files('src')
