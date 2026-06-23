import logging
import platform
import sys

from .constants import APP_NAME


def ensure_windows_platform() -> None:
    """Exit early when platform-specific Hyper-V features are unavailable."""
    if platform.system() == "Windows":
        return

    message = f"{APP_NAME} only runs on Windows with Hyper-V installed."
    logging.error("%s Current platform: %s", message, platform.platform())
    print(message, file=sys.stderr)
    raise SystemExit(1)
