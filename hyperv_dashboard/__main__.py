
import atexit
import logging
import socket
import sys
import threading
import time
import webbrowser

from . import config
from .constants import APP_NAME, APP_VERSION
from .logging_config import setup_logging
from .platform_guard import ensure_windows_platform
from .single_instance import acquire_single_instance_lock, release_single_instance_lock
from .state import load_message_ids


def open_browser() -> None:
    webbrowser.open(f"http://localhost:{config.PORT}")


def open_browser_when_ready(timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", int(config.PORT)), timeout=0.5):
                open_browser()
                return
        except OSError:
            time.sleep(0.25)

    logging.error("Timed out waiting for local server before opening browser")


def parse_args() -> None:
    if "--version" in sys.argv[1:]:
        print(f"{APP_NAME} {APP_VERSION}")
        raise SystemExit(0)


def main() -> None:
    parse_args()
    setup_logging()
    ensure_windows_platform()

    import uvicorn

    from .tray import run_tray
    from .versioning import maybe_check_for_updates_on_startup
    from .web import app

    config.reload_config()

    if not acquire_single_instance_lock():
        open_browser()
        return

    atexit.register(release_single_instance_lock)
    load_message_ids()

    threading.Thread(target=run_tray, daemon=True).start()
    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    logging.info("%s %s started", APP_NAME, APP_VERSION)
    maybe_check_for_updates_on_startup()

    uvicorn.run(app, host=config.HOST, port=config.PORT, log_config=None)


if __name__ == "__main__":
    main()
