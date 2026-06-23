import logging
import os
import sys
import webbrowser

from PIL import Image
from pystray import Icon, Menu, MenuItem

from . import config
from .constants import APP_NAME, CONFIG_FILE, LOG_FILE
from .icons import create_app_icon_image
from .single_instance import release_single_instance_lock
from .state import load_message_ids


def create_tray_image() -> Image.Image:
    return create_app_icon_image(64)


def tray_open_dashboard(icon: Image.Image, item: MenuItem) -> None:
    webbrowser.open(f"http://localhost:{config.PORT}")


def tray_open_config(icon: Image.Image, item: MenuItem) -> None:
    try:
        os.startfile(CONFIG_FILE)
    except Exception as exc:
        logging.error("Failed to open config: %s", exc)


def tray_reload_config(icon: Image.Image, item: MenuItem) -> None:
    try:
        config.reload_config()
        load_message_ids()
    except Exception as exc:
        logging.error("Failed to reload config: %s", exc)


def tray_open_logs(icon: Image.Image, item: MenuItem) -> None:
    try:
        os.startfile(LOG_FILE)
    except Exception as exc:
        logging.error("Failed to open logs: %s", exc)


def tray_check_for_updates(icon: Image.Image, item: MenuItem) -> None:
    webbrowser.open(f"http://localhost:{config.PORT}/version/check")


def tray_about(icon: Image.Image, item: MenuItem) -> None:
    webbrowser.open(f"http://localhost:{config.PORT}/version")


def tray_restart(icon: Image.Image, item: MenuItem) -> None:
    logging.info("Restarting application...")
    icon.stop()
    release_single_instance_lock()
    os.execv(sys.executable, [sys.executable])


def tray_exit(icon: Image.Image, item: MenuItem) -> None:
    icon.stop()
    os._exit(0)


def run_tray() -> None:
    icon = Icon(
        "HyperVDashboard",
        create_tray_image(),
        APP_NAME,
        Menu(
            MenuItem("Open Dashboard", tray_open_dashboard),
            MenuItem("Open Config", tray_open_config),
            MenuItem("Reload Config", tray_reload_config),
            MenuItem("Open Logs", tray_open_logs),
            MenuItem("Check for Updates", tray_check_for_updates),
            MenuItem("About", tray_about),
            MenuItem("Restart", tray_restart),
            MenuItem("Exit", tray_exit),
        ),
    )
    icon.run()
