import logging

from win11toast import toast

from . import config
from .constants import APP_ID
from .icons import generated_icon_path


def notify(title: str, message: str) -> None:
    with config.config_lock:
        notifications_enabled = config.NOTIFICATIONS_ENABLED

    if not notifications_enabled:
        return

    try:
        toast(
            title,
            message,
            app_id=APP_ID,
            icon=str(generated_icon_path()),
        )
    except Exception as exc:
        logging.error("Notification error: %s", exc)
