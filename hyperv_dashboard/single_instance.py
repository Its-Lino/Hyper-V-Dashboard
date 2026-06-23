import logging
from pathlib import Path
from typing import BinaryIO

from .constants import LOCK_FILE

_lock_handle: BinaryIO | None = None


def acquire_single_instance_lock(lock_file: Path = LOCK_FILE) -> bool:
    """Return False when another dashboard process already holds the lock."""
    global _lock_handle

    if _lock_handle is not None:
        return True

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_file.open("a+b")

    try:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        logging.info("Another %s instance is already running", lock_file.name)
        return False
    except Exception:
        handle.close()
        raise

    _lock_handle = handle
    return True


def release_single_instance_lock() -> None:
    global _lock_handle

    if _lock_handle is None:
        return

    try:
        import msvcrt

        _lock_handle.seek(0)
        msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
    except (ModuleNotFoundError, OSError) as exc:
        logging.debug("Failed to release single-instance lock cleanly: %s", exc)
    finally:
        _lock_handle.close()
        _lock_handle = None
