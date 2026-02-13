from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from flask import current_app

from .services.qso_import import import_qsos_for_user

_lock = Lock()
_running_ops: set[str] = set()
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=current_app.config.get("QSO_IMPORT_MAX_WORKERS", 2)
        )
    return _executor


def _clear_running(op: str) -> None:
    with _lock:
        _running_ops.discard(op)


def _run_import_job(app, op: str) -> None:
    with app.app_context():
        try:
            import_qsos_for_user(op=op)
        except Exception:
            current_app.logger.exception("Background QSO sync failed for %s", op)


def enqueue_qso_import(op: str) -> bool:
    app = current_app._get_current_object()
    with _lock:
        if op in _running_ops:
            return False
        _running_ops.add(op)

    future = _get_executor().submit(_run_import_job, app, op)
    future.add_done_callback(lambda _: _clear_running(op))
    return True


def is_qso_import_running(op: str) -> bool:
    with _lock:
        return op in _running_ops
