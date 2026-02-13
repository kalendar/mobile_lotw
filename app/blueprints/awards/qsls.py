from datetime import datetime, timezone

from flask import current_app, flash, render_template, request, session, url_for
from sqlalchemy.orm import Session

from ...background_jobs import enqueue_qso_import
from ...cache import is_expired
from ...database.queries import (
    check_unique_qsos_bulk,
    get_25_most_recent_rxqsls,
    get_user,
)
from ...database.table_declarations import QSOReport
from ...urls import QSLS_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsls")
@login_required(next_page="awards.qsls")
def qsls():
    force_reload: bool = request.args.get(
        "force_reload", default=False, type=bool
    )

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)

        qso_reports_last_update_time = user.qso_reports_last_update_time

        if qso_reports_last_update_time:
            qso_reports_last_update_time = datetime(
                year=qso_reports_last_update_time.year,
                month=qso_reports_last_update_time.month,
                day=qso_reports_last_update_time.day,
                hour=qso_reports_last_update_time.hour,
                minute=qso_reports_last_update_time.minute,
                second=qso_reports_last_update_time.second,
                microsecond=qso_reports_last_update_time.microsecond,
                tzinfo=timezone.utc,
            )

        if (
            not qso_reports_last_update_time
            or force_reload
            or is_expired(qso_reports_last_update_time, 60)
        ):
            current_app.logger.info("%s's QSOs are expired, starting sync.", user.op)
            started = enqueue_qso_import(op=user.op)
            if started:
                flash(
                    "Refreshing QSO data in the background. You can keep using the app.",
                    "info",
                )

        qsls: list[QSOReport] = get_25_most_recent_rxqsls(
            user=user, session=session_
        )

        # Bulk check uniqueness for all QSLs in one query
        uniqueness_map = check_unique_qsos_bulk(user, qsls, session_)
        qsl_tuples = [
            (
                qsl,
                qsl.seen,
                uniqueness_map.get(qsl.id, False),
            )
            for qsl in qsls
        ]

        for qsl in qsls:
            qsl.seen = True

        parsed_at = (
            user.qso_reports_last_update_time.strftime("%d/%m/%Y, %H:%M:%S")
            if user.qso_reports_last_update_time
            else "Pending initial sync"
        )
        lotw_health = {
            "state": user.lotw_auth_state or "unknown",
            "last_ok_at": user.lotw_last_ok_at.strftime("%d/%m/%Y, %H:%M:%S")
            if user.lotw_last_ok_at
            else "Never",
            "last_fail_at": user.lotw_last_fail_at.strftime("%d/%m/%Y, %H:%M:%S")
            if user.lotw_last_fail_at
            else "Never",
            "fail_count": user.lotw_fail_count or 0,
            "last_fail_reason": user.lotw_last_fail_reason,
        }
        qso_sync = {
            "status": user.qso_sync_status or "idle",
            "started_at": user.qso_sync_started_at.strftime("%d/%m/%Y, %H:%M:%S")
            if user.qso_sync_started_at
            else "N/A",
            "finished_at": user.qso_sync_finished_at.strftime("%d/%m/%Y, %H:%M:%S")
            if user.qso_sync_finished_at
            else "N/A",
            "last_error": user.qso_sync_last_error,
        }

        return render_template(
            "qsls.html",
            qsl_tuples=qsl_tuples,
            qsls_page_url=QSLS_PAGE_URL,
            parsed_at=parsed_at,
            user_op=user.op,
            lotw_health=lotw_health,
            qso_sync=qso_sync,
            force_reload=url_for("awards.qsls", force_reload=True),
            title="25 Most Recent QSLs",
        )
