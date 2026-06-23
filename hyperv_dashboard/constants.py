import os
from pathlib import Path

APP_NAME = "Hyper-V Dashboard"
APP_ID = "HyperVDashboard"
APP_VERSION = "1.0.0"
APP_CREATOR = "Its-Lino"
APP_REPOSITORY_URL = "https://github.com/Its-Lino/Hyper-V-Dashboard"

_configured_data_dir = os.getenv("HYPERV_DASHBOARD_DATA_DIR")
if _configured_data_dir:
    APP_DATA_DIR = Path(_configured_data_dir)
elif os.getenv("APPDATA"):
    APP_DATA_DIR = Path(os.environ["APPDATA"]) / APP_ID
else:
    APP_DATA_DIR = Path.home() / ".hyperv-dashboard"

CONFIG_FILE = APP_DATA_DIR / "config.json"
LOG_FILE = APP_DATA_DIR / "app.log"
LOCK_FILE = APP_DATA_DIR / "hyperv-dashboard.lock"
ICON_FILE = Path("assets/hyperv-dashboard.ico")

REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_LOG_MAX_BYTES = 1_000_000
DEFAULT_LOG_BACKUP_COUNT = 5
