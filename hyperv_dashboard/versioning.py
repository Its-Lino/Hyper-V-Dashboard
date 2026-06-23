import logging
import threading
from typing import Any

import requests

from . import config
from .constants import APP_NAME, APP_VERSION, REQUEST_TIMEOUT_SECONDS


def parse_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.strip().lstrip("v").split("."):
        if not part.isdigit():
            break
        parts.append(int(part))
    return tuple(parts)


def is_newer_version(latest_version: str, current_version: str = APP_VERSION) -> bool:
    latest = parse_version(latest_version)
    current = parse_version(current_version)
    return bool(latest and current and latest > current)


def fetch_latest_version() -> str | None:
    with config.config_lock:
        latest_version_url = config.LATEST_VERSION_URL

    if not latest_version_url:
        return None

    try:
        response = requests.get(latest_version_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.error("Failed to check latest version: %s", exc)
        return None

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = response.json()
        except ValueError as exc:
            logging.error("Latest version endpoint returned invalid JSON: %s", exc)
            return None

        if not isinstance(payload, dict):
            logging.error("Latest version endpoint returned unexpected JSON")
            return None

        latest_version = payload.get("version") or payload.get("tag_name")
    else:
        latest_version = response.text.strip()

    return str(latest_version).strip().lstrip("v") if latest_version else None


def check_for_updates() -> dict[str, Any]:
    latest_version = fetch_latest_version()
    update_available = (
        is_newer_version(latest_version) if latest_version is not None else False
    )

    result = {
        "app": APP_NAME,
        "current_version": APP_VERSION,
        "latest_version": latest_version,
        "update_available": update_available,
    }

    if update_available:
        logging.info("Update available: %s", latest_version)

    return result


def maybe_check_for_updates_on_startup() -> None:
    with config.config_lock:
        check_enabled = config.CHECK_FOR_UPDATES

    if check_enabled:
        threading.Thread(target=check_for_updates, daemon=True).start()
