import json
import logging
import subprocess
from typing import Any

from fastapi import HTTPException

from .constants import APP_NAME
from .discord import update_or_send_message
from .notifications import notify
from .state import last_vm_states, state_lock


def powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps(command: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except Exception as exc:
        logging.error("PowerShell execution failed: %s", exc)
        return {"stdout": "", "stderr": str(exc)}

    if result.returncode != 0 and result.stderr:
        logging.error("PowerShell command failed: %s", result.stderr.strip())

    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def get_vm_signature(vm: dict[str, Any]) -> tuple[Any, ...]:
    return (
        vm.get("State"),
        vm.get("Heartbeat"),
        vm.get("Status"),
        vm.get("UptimeFormatted"),
    )


def format_bytes(value: Any) -> str:
    try:
        bytes_value = int(value)
    except (TypeError, ValueError):
        return "N/A"

    if bytes_value <= 0:
        return "N/A"

    units = ("B", "KB", "MB", "GB", "TB")
    size = float(bytes_value)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def normalize_vm_data(data: Any) -> list[dict[str, Any]]:
    if not data:
        return []

    if isinstance(data, dict):
        return [data]

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    logging.error("Unexpected VM data shape: %s", type(data).__name__)
    return []


def list_vms() -> list[dict[str, Any]]:
    command = """
    Get-VM | Select-Object Name,
    @{Name="State";Expression={$_.State.ToString()}},
    Status,
    CPUUsage,
    ProcessorCount,
    MemoryAssigned,
    MemoryDemand,
    @{Name="Heartbeat";Expression={
        (Get-VMIntegrationService -VMName $_.Name | Where-Object {$_.Name -eq "Heartbeat"}).PrimaryStatusDescription
    }},
    @{Name="Uptime";Expression={"$($_.Uptime.Days)d $($_.Uptime.Hours)h $($_.Uptime.Minutes)m"}} |
    ConvertTo-Json -Depth 3
    """

    result = run_ps(command)
    output = result["stdout"]

    if not output:
        return []

    try:
        parsed_data = json.loads(output)
    except json.JSONDecodeError as exc:
        logging.error("JSON parse error: %s | output=%s", exc, output)
        return []

    vms = normalize_vm_data(parsed_data)

    for vm in vms:
        vm["UptimeFormatted"] = vm.get("Uptime", "N/A")
        vm["Heartbeat"] = vm.get("Heartbeat", "Unknown")
        vm["CPUUsageFormatted"] = f"{vm.get('CPUUsage', 0) or 0}%"
        vm["ProcessorCountFormatted"] = str(vm.get("ProcessorCount") or "N/A")
        vm["MemoryAssignedFormatted"] = format_bytes(vm.get("MemoryAssigned"))
        vm["MemoryUsedFormatted"] = format_bytes(vm.get("MemoryDemand"))

        name = vm.get("Name")
        if not name:
            logging.error("Skipping VM without a name: %s", vm)
            continue

        signature = get_vm_signature(vm)
        with state_lock:
            old_signature = last_vm_states.get(name)

        if old_signature != signature:
            update_or_send_message(vm)

        with state_lock:
            last_vm_states[name] = signature

    return vms


def run_vm_action(
    name: str, action: str, success_status: str, force: bool = False
) -> dict[str, str]:
    command = f"{action} -Name {powershell_quote(name)}"
    if force:
        command += " -Force"

    result = run_ps(command)
    if result["stderr"]:
        notify(APP_NAME, f"{name}: {action} failed")
        raise HTTPException(status_code=500, detail=result["stderr"])

    notify(APP_NAME, f"{name}: {success_status}")
    return {"status": success_status}
