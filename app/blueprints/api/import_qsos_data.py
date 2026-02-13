from flask import current_app, redirect, request, session, url_for

from ...background_jobs import enqueue_qso_import
from ...services.qso_import import import_qsos_for_user
from ..auth.wrappers import login_required, paid_required
from .base import bp


@bp.get("/api/v1/import_qsos_data")
@login_required()
@paid_required()
def import_qsos_data():
    op = session.get("op")
    if not op:
        return redirect(url_for("auth.login"))
    run_async = request.args.get("async", type=bool, default=False)

    if run_async:
        started = enqueue_qso_import(op=op)
        if started:
            current_app.logger.info("Started background QSO sync for %s", op)
        else:
            current_app.logger.info(
                "Background QSO sync already in progress for %s", op
            )
        return redirect(url_for("awards.qsls"))

    import_qsos_for_user(op=op)
    return redirect(url_for("awards.qsls"))
