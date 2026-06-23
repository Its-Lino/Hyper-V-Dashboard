import logging
from datetime import datetime
from typing import Any

import requests

from . import config
from .constants import REQUEST_TIMEOUT_SECONDS
from .state import save_message_ids, state_lock, vm_message_ids


def build_embed(vm: dict[str, Any]) -> dict[str, Any]:
    def safe(value: Any) -> str:
        return str(value) if value else "Unknown"

    state = safe(vm.get("State"))
    heartbeat = safe(vm.get("Heartbeat"))
    uptime = safe(vm.get("UptimeFormatted"))
    status = safe(vm.get("Status"))
    cpu_usage = safe(vm.get("CPUUsageFormatted"))
    memory_assigned = safe(vm.get("MemoryAssignedFormatted"))
    memory_used = safe(vm.get("MemoryUsedFormatted"))

    if heartbeat == "No Contact":
        color = 0xFACC15
    elif state == "Running":
        color = 0x22C55E
    else:
        color = 0xEF4444

    return {
        "title": f"VM: {vm.get('Name', 'Unknown')}",
        "description": "VM status update",
        "color": color,
        "fields": [
            {"name": "State", "value": state, "inline": True},
            {"name": "Heartbeat", "value": heartbeat, "inline": True},
            {"name": "Uptime", "value": uptime, "inline": True},
            {"name": "CPU Usage", "value": cpu_usage, "inline": True},
            {"name": "Memory Assigned", "value": memory_assigned, "inline": True},
            {"name": "Memory Used", "value": memory_used, "inline": True},
            {"name": "Status", "value": status[:1024], "inline": False},
        ],
        "footer": {
            "text": f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        },
    }


def update_or_send_message(vm: dict[str, Any]) -> None:
    name = vm.get("Name")
    if not name:
        logging.error("Cannot update Discord message for VM without a name: %s", vm)
        return

    embed = build_embed(vm)

    with config.config_lock:
        webhooks = list(config.DISCORD_WEBHOOKS)

    for webhook in webhooks:
        with state_lock:
            webhook_message_ids = vm_message_ids.setdefault(name, {})
            message_id = webhook_message_ids.get(webhook)

        try:
            if message_id:
                response = requests.patch(
                    f"{webhook}/messages/{message_id}",
                    json={"embeds": [embed]},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            else:
                response = requests.post(
                    f"{webhook}?wait=true",
                    json={"embeds": [embed]},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

            if response.status_code not in (200, 204):
                logging.error(
                    "Discord request failed: %s %s",
                    response.status_code,
                    response.text,
                )
                continue

            if not message_id:
                with state_lock:
                    vm_message_ids.setdefault(name, {})[webhook] = response.json()["id"]
                save_message_ids()
        except (requests.RequestException, KeyError, ValueError) as exc:
            logging.error("Discord error: %s", exc)
