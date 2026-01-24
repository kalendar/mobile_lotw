from datetime import datetime, timezone

from flask import current_app, render_template, request, session, url_for
from sqlalchemy.orm import Session

from ...cache import is_expired
from ...database.queries import (
    check_unique_qsos_bulk,
    get_25_most_recent_rxqsls,
    get_user,
)
from ...database.table_declarations import QSOReport
from ...urls import QSLS_PAGE_URL
from ..api.import_qsos_data import import_qsos_data
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
            current_app.logger.info(f"{user.op}'s QSOs are expired, importing.")
            import_qsos_data()

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

        parsed_at = user.qso_reports_last_update_time.strftime(
            "%d/%m/%Y, %H:%M:%S"
        )

        return render_template(
            "qsls.html",
            qsl_tuples=qsl_tuples,
            qsls_page_url=QSLS_PAGE_URL,
            parsed_at=parsed_at,
            user_op=user.op,
            force_reload=url_for("awards.qsls", force_reload=True),
            title="25 Most Recent QSLs",
        )
