import json
import logging
import threading
from copy import deepcopy
from typing import Any

from . import config

state_lock = threading.RLock()
last_vm_states: dict[str, tuple[Any, ...]] = {}
vm_message_ids: dict[str, dict[str, str]] = {}


def load_message_ids() -> None:
    with config.config_lock:
        message_state_file = config.MESSAGE_STATE_FILE

    if not message_state_file.exists():
        return

    try:
        with message_state_file.open("r", encoding="utf-8") as file:
            loaded_message_ids = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to load Discord message state: %s", exc)
        return

    if not isinstance(loaded_message_ids, dict):
        logging.error("Ignoring invalid Discord message state file")
        return

    with state_lock:
        vm_message_ids.clear()
        for name, webhook_ids in loaded_message_ids.items():
            if isinstance(name, str) and isinstance(webhook_ids, dict):
                vm_message_ids[name] = {
                    str(webhook): str(message_id)
                    for webhook, message_id in webhook_ids.items()
                }


def save_message_ids() -> None:
    with config.config_lock:
        message_state_file = config.MESSAGE_STATE_FILE

    with state_lock:
        snapshot = deepcopy(vm_message_ids)

    try:
        message_state_file.parent.mkdir(parents=True, exist_ok=True)
        with message_state_file.open("w", encoding="utf-8") as file:
            json.dump(snapshot, file, indent=4)
    except OSError as exc:
        logging.error("Failed to save Discord message state: %s", exc)
