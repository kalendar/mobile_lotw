from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..table_declarations import QSOReport, User


def ensure_user(op: str, session: Session) -> User:
    user = session.scalar(select(User).where(User.op == op))

    if not user:
        user = User(op=op)

    return user


def get_object[T](type_: T, id: int, session: Session) -> T | None:
    return session.scalar(select(type_).where(type_.id == id))


def get_user(op: str, session: Session) -> User:
    user = session.scalar(select(User).where(User.op == op))

    if not user:
        raise ValueError(f"No user with op={op} found!")

    return user


def is_unique_qso(user: User, qso: QSOReport, session: Session) -> bool:
    # fmt: off
    CW = ["CW"]
    DIGITAL_TYPES = [
        "ATV", "FAX", "SSTV", "AMTOR", "ARDOP", "CHIP", "CLOVER",
        "CONTESTI", "DATA", "DOMINO", "FESK", "FSK31", "FSK441", "FST4", "FT4",
        "FT8", "GTOR", "HELL", "HFSK", "ISCAT", "JT4", "JT65",
        "JT6M", "JT9", "MFSK16", "MFSK8", "MINIRTTY", "MSK144",
        "MT63", "OLIVIA", "OPERA", "PACKET", "PACTOR", "PAX", "PSK10",
        "PSK125", "PSK2K", "PSK31", "PSK63", "PSK63F", "PSKAM", "PSKFEC31",
        "Q15", "Q65", "QRA64", "ROS", "RTTY", "RTTYM", "T10", "THOR", "THROB",
        "VOI", "WINMOR", "WSPR", "IMAGE", "DATA"
    ]
    PHONE_TYPES = ["PHONE", "AM", "C4FM", "DIGITALVOICE", "DSTAR", "FM", "SSB"]
    # fmt: on

    if qso.mode in CW:
        general_type = CW
    elif qso.mode in DIGITAL_TYPES:
        general_type = DIGITAL_TYPES
    elif qso.mode in PHONE_TYPES:
        general_type = PHONE_TYPES
    else:
        general_type = DIGITAL_TYPES

    stmt = (
        select(func.count())
        .select_from(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.mode.in_(general_type),
                QSOReport.dxcc == qso.dxcc,
                QSOReport.band == qso.band,
                QSOReport.id != qso.id,
            )
        )
    )

    return not session.scalar(statement=stmt)


# Mode type constants for uniqueness checks
_CW = frozenset(["CW"])
_DIGITAL_TYPES = frozenset([
    "ATV", "FAX", "SSTV", "AMTOR", "ARDOP", "CHIP", "CLOVER",
    "CONTESTI", "DATA", "DOMINO", "FESK", "FSK31", "FSK441", "FST4", "FT4",
    "FT8", "GTOR", "HELL", "HFSK", "ISCAT", "JT4", "JT65",
    "JT6M", "JT9", "MFSK16", "MFSK8", "MINIRTTY", "MSK144",
    "MT63", "OLIVIA", "OPERA", "PACKET", "PACTOR", "PAX", "PSK10",
    "PSK125", "PSK2K", "PSK31", "PSK63", "PSK63F", "PSKAM", "PSKFEC31",
    "Q15", "Q65", "QRA64", "ROS", "RTTY", "RTTYM", "T10", "THOR", "THROB",
    "VOI", "WINMOR", "WSPR", "IMAGE",
])
_PHONE_TYPES = frozenset(["PHONE", "AM", "C4FM", "DIGITALVOICE", "DSTAR", "FM", "SSB"])


def _get_mode_group(mode: str) -> str:
    """Return mode group identifier for a given mode."""
    if mode in _CW:
        return "CW"
    elif mode in _PHONE_TYPES:
        return "PHONE"
    else:
        return "DIGITAL"


def check_unique_qsos_bulk(
    user: User, qsos: list[QSOReport], session: Session
) -> dict[int, bool]:
    """Check uniqueness for multiple QSOs in fewer queries.

    Returns dict mapping QSO id -> is_unique (True if first QSO for that
    mode_group/dxcc/band combination).
    """
    if not qsos:
        return {}

    # Get unique (dxcc, band) pairs to query
    dxcc_band_pairs = {(qso.dxcc, qso.band) for qso in qsos}

    # Single query to get all user's QSOs matching these (dxcc, band) pairs
    conditions = [
        and_(QSOReport.dxcc == dxcc, QSOReport.band == band)
        for dxcc, band in dxcc_band_pairs
    ]

    stmt = (
        select(QSOReport.id, QSOReport.mode, QSOReport.dxcc, QSOReport.band)
        .join(User)
        .where(and_(User.id == user.id, or_(*conditions)))
    )

    all_matching = session.execute(stmt).fetchall()

    # Build lookup: (mode_group, dxcc, band) -> set of ids
    combo_to_ids: dict[tuple[str, str, str], set[int]] = {}
    for row in all_matching:
        qso_id, mode, dxcc, band = row
        mode_group = _get_mode_group(mode)
        key = (mode_group, dxcc, band)
        if key not in combo_to_ids:
            combo_to_ids[key] = set()
        combo_to_ids[key].add(qso_id)

    # Check uniqueness for each QSO we're interested in
    result = {}
    for qso in qsos:
        mode_group = _get_mode_group(qso.mode)
        key = (mode_group, qso.dxcc, qso.band)
        ids_with_combo = combo_to_ids.get(key, set())
        # Unique if this QSO is the only one with this combination
        # (or equivalently, if removing this QSO leaves no others)
        other_count = len(ids_with_combo - {qso.id})
        result[qso.id] = other_count == 0

    return result


def get_qso_report_by_timestamp(
    app_lotw_qso_timestamp: datetime, call: str, session: Session
) -> QSOReport | None:
    return session.scalar(
        select(QSOReport).where(
            and_(
                QSOReport.app_lotw_qso_timestamp == app_lotw_qso_timestamp,
                QSOReport.call == call,
            )
        )
    )


def get_qso_reports_by_timestamps(
    timestamp_call_pairs: list[tuple[datetime, str]], session: Session
) -> dict[tuple[datetime, str], QSOReport]:
    """Fetch multiple QSO reports by (timestamp, call) pairs in a single query."""
    if not timestamp_call_pairs:
        return {}

    conditions = [
        and_(
            QSOReport.app_lotw_qso_timestamp == ts,
            QSOReport.call == call,
        )
        for ts, call in timestamp_call_pairs
    ]

    stmt = select(QSOReport).where(or_(*conditions))
    reports = session.scalars(stmt).all()

    return {
        (report.app_lotw_qso_timestamp, report.call): report for report in reports
    }
