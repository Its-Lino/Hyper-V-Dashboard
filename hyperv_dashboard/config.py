import json
import logging
import secrets
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_FILE,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
)
from .logging_config import setup_logging

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "refresh_interval": 2,
    },
    "discord": {
        "webhooks": [],
        "message_state_file": "vm_message_ids.json",
    },
    "notifications": {
        "enabled": True,
    },
    "updates": {
        "latest_version_url": "https://api.github.com/repos/Its-Lino/Hyper-V-Dashboard/releases/latest",
        "check_for_updates": False,
    },
    "logging": {
        "max_bytes": DEFAULT_LOG_MAX_BYTES,
        "backup_count": DEFAULT_LOG_BACKUP_COUNT,
    },
    "auth": {
        "enabled": True,
        "password_hash": "",
        "secret_key": "",
        "remember_days": 30,
        "session_hours": 8,
        "setup_allowed": True,
    },
}

config_lock = threading.RLock()
config: dict[str, Any] = {}

DISCORD_WEBHOOKS: list[str] = []
HOST = DEFAULT_CONFIG["server"]["host"]
PORT = DEFAULT_CONFIG["server"]["port"]
REFRESH_INTERVAL = DEFAULT_CONFIG["server"]["refresh_interval"]
NOTIFICATIONS_ENABLED = DEFAULT_CONFIG["notifications"]["enabled"]
MESSAGE_STATE_FILE = Path(DEFAULT_CONFIG["discord"]["message_state_file"])
LATEST_VERSION_URL = DEFAULT_CONFIG["updates"]["latest_version_url"]
CHECK_FOR_UPDATES = DEFAULT_CONFIG["updates"]["check_for_updates"]
LOG_MAX_BYTES = DEFAULT_CONFIG["logging"]["max_bytes"]
LOG_BACKUP_COUNT = DEFAULT_CONFIG["logging"]["backup_count"]
AUTH_COOKIE_NAME = "hvd_session"
AUTH_ENABLED = DEFAULT_CONFIG["auth"]["enabled"]
AUTH_PASSWORD_HASH = DEFAULT_CONFIG["auth"]["password_hash"]
AUTH_SECRET_KEY = DEFAULT_CONFIG["auth"]["secret_key"]
AUTH_REMEMBER_DAYS = DEFAULT_CONFIG["auth"]["remember_days"]
AUTH_SESSION_HOURS = DEFAULT_CONFIG["auth"]["session_hours"]
AUTH_SETUP_ALLOWED = DEFAULT_CONFIG["auth"]["setup_allowed"]


def default_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_CONFIG)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def create_default_config() -> dict[str, Any]:
    default = default_config()
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as file:
        json.dump(default, file, indent=4)

    logging.info("Created default config at %s", CONFIG_FILE)
    return default


def save_config_file(config_to_save: dict[str, Any]) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as file:
            json.dump(config_to_save, file, indent=4)
    except OSError as exc:
        logging.error("Failed to save config: %s", exc)


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return create_default_config()

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to load config, using defaults: %s", exc)
        return default_config()

    merged_config = deep_merge(default_config(), loaded_config)
    if not merged_config["updates"].get("latest_version_url"):
        merged_config["updates"]["latest_version_url"] = DEFAULT_CONFIG["updates"][
            "latest_version_url"
        ]
    return merged_config


def apply_config(loaded_config: dict[str, Any]) -> None:
    global AUTH_ENABLED
    global AUTH_PASSWORD_HASH
    global AUTH_REMEMBER_DAYS
    global AUTH_SECRET_KEY
    global AUTH_SESSION_HOURS
    global AUTH_SETUP_ALLOWED
    global CHECK_FOR_UPDATES
    global DISCORD_WEBHOOKS
    global HOST
    global LATEST_VERSION_URL
    global LOG_BACKUP_COUNT
    global LOG_MAX_BYTES
    global MESSAGE_STATE_FILE
    global NOTIFICATIONS_ENABLED
    global PORT
    global REFRESH_INTERVAL
    global config

    should_save_config = False

    with config_lock:
        config = loaded_config
        server_config = config.get("server", {})
        discord_config = config.get("discord", {})
        notification_config = config.get("notifications", {})
        updates_config = config.get("updates", {})
        logging_config = config.get("logging", {})
        auth_config = config.get("auth", {})

        DISCORD_WEBHOOKS = list(
            discord_config.get("webhooks", DEFAULT_CONFIG["discord"]["webhooks"])
        )
        HOST = str(server_config.get("host", DEFAULT_CONFIG["server"]["host"]))
        PORT = int(server_config.get("port", DEFAULT_CONFIG["server"]["port"]))
        REFRESH_INTERVAL = float(
            server_config.get(
                "refresh_interval",
                DEFAULT_CONFIG["server"]["refresh_interval"],
            )
        )
        NOTIFICATIONS_ENABLED = bool(
            notification_config.get(
                "enabled",
                DEFAULT_CONFIG["notifications"]["enabled"],
            )
        )
        configured_message_state_file = Path(
            str(
                discord_config.get(
                    "message_state_file",
                    DEFAULT_CONFIG["discord"]["message_state_file"],
                )
            )
        )
        if not configured_message_state_file.is_absolute():
            configured_message_state_file = CONFIG_FILE.parent / configured_message_state_file
        MESSAGE_STATE_FILE = configured_message_state_file
        LATEST_VERSION_URL = str(
            updates_config.get(
                "latest_version_url",
                DEFAULT_CONFIG["updates"]["latest_version_url"],
            )
        )
        CHECK_FOR_UPDATES = bool(
            updates_config.get(
                "check_for_updates",
                DEFAULT_CONFIG["updates"]["check_for_updates"],
            )
        )
        LOG_MAX_BYTES = int(
            logging_config.get(
                "max_bytes",
                DEFAULT_CONFIG["logging"]["max_bytes"],
            )
        )
        LOG_BACKUP_COUNT = int(
            logging_config.get(
                "backup_count",
                DEFAULT_CONFIG["logging"]["backup_count"],
            )
        )

        AUTH_ENABLED = bool(auth_config.get("enabled", DEFAULT_CONFIG["auth"]["enabled"]))
        AUTH_PASSWORD_HASH = str(
            auth_config.get("password_hash", DEFAULT_CONFIG["auth"]["password_hash"])
        )
        AUTH_SECRET_KEY = str(
            auth_config.get("secret_key", DEFAULT_CONFIG["auth"]["secret_key"])
        )
        AUTH_REMEMBER_DAYS = int(
            auth_config.get("remember_days", DEFAULT_CONFIG["auth"]["remember_days"])
        )
        AUTH_SESSION_HOURS = int(
            auth_config.get("session_hours", DEFAULT_CONFIG["auth"]["session_hours"])
        )
        AUTH_SETUP_ALLOWED = bool(
            auth_config.get("setup_allowed", DEFAULT_CONFIG["auth"]["setup_allowed"])
        )

        if AUTH_ENABLED and not AUTH_SECRET_KEY:
            AUTH_SECRET_KEY = secrets.token_urlsafe(48)
            config.setdefault("auth", {})["secret_key"] = AUTH_SECRET_KEY
            should_save_config = True

    setup_logging(LOG_MAX_BYTES, LOG_BACKUP_COUNT)

    if should_save_config:
        save_config_file(config)


def reload_config() -> dict[str, Any]:
    loaded_config = load_config()
    apply_config(loaded_config)
    logging.info("Config reloaded successfully")
    return loaded_config
