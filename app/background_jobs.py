from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from flask import current_app

from .services.qso_import import import_qsos_for_user

_lock = Lock()
_running_ops: set[str] = set()
_executor: ThreadPoolExecutor | None = None
_digest_lock = Lock()
_digest_running = False
_digest_delivery_lock = Lock()
_digest_delivery_running = False


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


def _set_digest_running(value: bool) -> None:
    global _digest_running
    with _digest_lock:
        _digest_running = value


def _run_qsl_digest_job(app) -> None:
    with app.app_context():
        from .services.qsl_digest import run_due_qsl_digest_generation

        try:
            result = run_due_qsl_digest_generation()
            current_app.logger.info("QSL digest run complete: %s", result)
        except Exception:
            current_app.logger.exception("QSL digest run failed")
        finally:
            _set_digest_running(False)


def enqueue_qsl_digest_generation() -> bool:
    global _digest_running
    app = current_app._get_current_object()
    with _digest_lock:
        if _digest_running:
            return False
        _digest_running = True

    _get_executor().submit(_run_qsl_digest_job, app)
    return True


def is_qsl_digest_generation_running() -> bool:
    with _digest_lock:
        return _digest_running


def _set_digest_delivery_running(value: bool) -> None:
    global _digest_delivery_running
    with _digest_delivery_lock:
        _digest_delivery_running = value


def _run_qsl_digest_delivery_job(app) -> None:
    with app.app_context():
        from .services.digest_notifications import dispatch_pending_digest_notifications

        try:
            result = dispatch_pending_digest_notifications()
            current_app.logger.info("QSL digest delivery run complete: %s", result)
        except Exception:
            current_app.logger.exception("QSL digest delivery run failed")
        finally:
            _set_digest_delivery_running(False)


def enqueue_qsl_digest_delivery() -> bool:
    global _digest_delivery_running
    app = current_app._get_current_object()
    with _digest_delivery_lock:
        if _digest_delivery_running:
            return False
        _digest_delivery_running = True

    _get_executor().submit(_run_qsl_digest_delivery_job, app)
    return True


def is_qsl_digest_delivery_running() -> bool:
    with _digest_delivery_lock:
        return _digest_delivery_running
