
# Hyper-V Dashboard

FastAPI based dashboard for managing local Hyper-V Virtual Machines remotely.

## Requirements

- Windows with Hyper-V enabled
- Python 3.10+
- PowerShell access to Hyper-V cmdlets

## Installation

1. Download the latest `.exe` from **[Releases](https://github.com/Its-Lino/Hyper-V-Dashboard/releases)**
2. Run the application

The app creates config, logs, and Discord message state under the current user's
app-data directory on first run. Set `HYPERV_DASHBOARD_DATA_DIR` to override
that location for testing or portable runs.

Only one dashboard instance can run at a time. Starting the app again opens the
existing dashboard instead of launching a second tray/server process.

### Authentication

Authentication is enabled by default. On first launch, the dashboard redirects to
a setup page where you create the local admin password.

Login supports two session modes:

- **Remember this device**: stores a signed cookie for the configured number of
  days.
- **One-time browser session**: stores a session cookie that expires when the
  browser session ends, with a server-side expiration as a backstop.

Auth settings are stored in `config.json`:

```json
{
  "server": {
    "host": "127.0.0.1"
  },
  "auth": {
    "enabled": true,
    "remember_days": 30,
    "session_hours": 8
  }
}
```

The password is stored as a PBKDF2 hash, not as plain text. If you forget the
password, stop the app and clear `auth.password_hash` in `config.json` to run
the setup flow again.

## Configuration

Settings are stored in `config.json`. Which can be accessed quickly by right clicking the app in the system tray, and clicking `open config`. 

Example:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "notifications": {
    "enabled": true
  },
  "auth": {
    "enabled": true,
    "remember_days": 30,
    "session_hours": 8
  }
}
```

## Build a Windows executable

Install runtime and build dependencies:

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
```

Generate the Windows icon:

```powershell
python scripts/generate_icon.py --output assets/hyperv-dashboard.ico
```

Build with PyInstaller:

```powershell
pyinstaller --onefile --paths . --add-data "templates;templates" --add-data "assets;assets" --hidden-import pystray --hidden-import PIL --name HyperVDashboard --uac-admin --noconsole --icon assets/hyperv-dashboard.ico scripts/pyinstaller_entry.py
```

The executable is written to `dist\HyperVDashboard.exe`.
