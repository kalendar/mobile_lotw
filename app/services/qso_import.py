from datetime import datetime, timezone
from io import BytesIO
from itertools import batched

from adi_parser import parse_adi
from adi_parser.dataclasses import QSOReport as DCQSOReport
from flask import current_app
from sqlalchemy.orm import Session

from .. import lotw
from ..database.queries import (
    get_qso_reports_by_timestamps,
    get_user,
)
from ..database.table_declarations import QSOReport
from ..urls import QSOS_URL


def _report_key(qso_report: DCQSOReport) -> tuple[datetime | None, str | None]:
    return (qso_report.app_lotw_qso_timestamp, qso_report.call)


def _prefer_incoming_report(existing: DCQSOReport, incoming: DCQSOReport) -> bool:
    existing_score = (
        1 if existing.app_lotw_rxqsl is not None else 0,
        1 if existing.app_lotw_rxqso is not None else 0,
    )
    incoming_score = (
        1 if incoming.app_lotw_rxqsl is not None else 0,
        1 if incoming.app_lotw_rxqso is not None else 0,
    )
    return incoming_score > existing_score


def _set_qso_sync_state(
    op: str,
    status: str,
    *,
    error: str | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    now = datetime.now(tz=timezone.utc)
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)
        user.qso_sync_status = status
        if started:
            user.qso_sync_started_at = now
            user.qso_sync_finished_at = None
        if finished:
            user.qso_sync_finished_at = now
        user.qso_sync_last_error = error


def _add_reports_to_db(
    *,
    qso_reports: list[DCQSOReport],
    user_id: int,
    has_imported: bool,
    session_: Session,
) -> tuple[int, int]:
    deduped_reports: dict[tuple[datetime | None, str | None], DCQSOReport] = {}
    for qso_report in qso_reports:
        key = _report_key(qso_report)
        existing = deduped_reports.get(key)
        if existing is None or _prefer_incoming_report(existing, qso_report):
            deduped_reports[key] = qso_report
    unique_reports = list(deduped_reports.values())
    duplicate_count = len(qso_reports) - len(unique_reports)
    if duplicate_count > 0:
        current_app.logger.warning(
            "Collapsed %s duplicate QSO rows from LoTW payload for user_id=%s",
            duplicate_count,
            user_id,
        )

    # Bulk fetch existing reports if user has imported before
    existing_reports: dict = {}
    if has_imported:
        timestamp_call_pairs = [_report_key(qr) for qr in unique_reports]
        existing_reports = get_qso_reports_by_timestamps(
            timestamp_call_pairs, user_id, session_
        )

    inserted = 0
    updated = 0
    for qso_report in unique_reports:
        key = _report_key(qso_report)
        report = existing_reports.get(key) if has_imported else None

        if not report:
            current_app.logger.debug(
                "Adding QSO at %s for user_id=%s to DB",
                qso_report.app_lotw_qso_timestamp,
                user_id,
            )

            session_.add(
                QSOReport(
                    user_id=user_id,
                    dataclass=qso_report,
                )
            )
            inserted += 1
            continue

        mutated = (
            report.app_lotw_rxqso != qso_report.app_lotw_rxqso
            or report.app_lotw_rxqsl != qso_report.app_lotw_rxqsl
        )
        if mutated:
            report.app_lotw_rxqso = qso_report.app_lotw_rxqso
            report.app_lotw_rxqsl = qso_report.app_lotw_rxqsl
            updated += 1

    return inserted, updated


def import_qsos_for_user(op: str) -> dict[str, int]:
    _set_qso_sync_state(op, "syncing", started=True)

    try:
        user_op: str
        qso_reports_last_update: datetime
        has_imported: bool
        user_id: int

        with current_app.config.get("SESSION_MAKER").begin() as session_:
            user = get_user(op=op, session=session_)
            user_op = user.op
            user_id = user.id
            qso_reports_last_update = user.qso_reports_last_update
            has_imported = user.has_imported

        current_app.logger.info("Updating %s's QSOs", user_op)

        url = QSOS_URL.format(qso_reports_last_update.strftime("%Y-%m-%d"))
        current_app.logger.info("Getting %s's QSOs from LoTW", user_op)
        response = lotw.get(url=url, op=op)

        if "Page Request Limit!" in response.text:
            raise RuntimeError("LoTW page request limit reached.")

        current_app.logger.info("Got %s's QSOs from LoTW", user_op)
        adi_file = BytesIO(response.content)

        current_app.logger.info("Parsing %s's QSOs", user_op)
        _, qso_reports = parse_adi(file=adi_file)
        current_app.logger.info("Parsed %s QSOs for %s", len(qso_reports), user_op)

        inserted_total = 0
        updated_total = 0
        with current_app.config.get("SESSION_MAKER").begin() as session_:
            for qso_reports_subset in batched(qso_reports, 200):
                inserted, updated = _add_reports_to_db(
                    qso_reports=qso_reports_subset,
                    user_id=user_id,
                    has_imported=has_imported,
                    session_=session_,
                )
                inserted_total += inserted
                updated_total += updated

            user = get_user(op=op, session=session_)
            now = datetime.now(tz=timezone.utc)
            user.qso_reports_last_update = now.date()
            user.qso_reports_last_update_time = now
            user.has_imported = True

        _set_qso_sync_state(op, "idle", finished=True)
        current_app.logger.info("Done updating QSOs for %s", user_op)
        return {
            "fetched": len(qso_reports),
            "inserted": inserted_total,
            "updated": updated_total,
        }
    except Exception as error:
        _set_qso_sync_state(
            op,
            "failed",
            error=str(error),
            finished=True,
        )
        raise
