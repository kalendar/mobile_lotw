from datetime import datetime, timezone

from flask import current_app, render_template, request, session, url_for
from sqlalchemy.orm import Session

from ...cache import is_expired
from ...database.queries import get_user
from ...urls import QSLS_PAGE_URL
from ..api.import_qsos_data import import_qsos_data
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsls")
@login_required(next_page="awards.qsls")
def qsls():
    number_of_qsls: int = request.args.get("show", default=0, type=int) or 25
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
            current_app.logger.info(
                f"{user.op}'s QSO's are expired, importing."
            )
            import_qsos_data()

        qso_reports_len = len(user.qso_reports)

        qsls = user.qso_reports[: min(qso_reports_len, number_of_qsls)]

        qsl_tuples = [(qsl, qsl.seen) for qsl in qsls]

        for qsl in qsls:
            qsl.seen = True

        return render_template(
            "qsls.html",
            qsl_tuples=qsl_tuples,
            qsls_page_url=QSLS_PAGE_URL,
            parsed_at=user.qso_reports_last_update_time,
            force_reload=url_for("awards.qsls", force_reload=True),
            title=f"{number_of_qsls} Most Recent QSLs",
        )
