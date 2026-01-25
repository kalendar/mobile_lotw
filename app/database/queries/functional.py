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
    """Check if a QSO would earn DXCC credit by filling an unfilled slot.

    DXCC has two independent slot types:
    1. Band slots: (dxcc, band) - e.g., "10M + Bonaire"
    2. Mode slots: (dxcc, mode_group) - e.g., "Phone + Bonaire"

    A QSO is "unique" if it fills at least one unfilled slot.
    Only QSOs with app_lotw_credit_granted set count as filling slots.
    """
    mode_group = _get_mode_group(qso.mode)

    # Check if band slot (dxcc, band) is already filled by a credited QSO
    band_slot_filled = session.scalar(
        select(func.count())
        .select_from(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.dxcc == qso.dxcc,
                QSOReport.band == qso.band,
                QSOReport.app_lotw_credit_granted.isnot(None),
                QSOReport.id != qso.id,
            )
        )
    )

    # Check if mode slot (dxcc, mode_group) is already filled by a credited QSO
    mode_slot_filled = session.scalar(
        select(func.count())
        .select_from(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.dxcc == qso.dxcc,
                QSOReport.mode.in_(_CW if mode_group == "CW" else
                                   _PHONE_TYPES if mode_group == "PHONE" else
                                   _DIGITAL_TYPES),
                QSOReport.app_lotw_credit_granted.isnot(None),
                QSOReport.id != qso.id,
            )
        )
    )

    # Unique if EITHER slot is unfilled
    is_new_band_slot = band_slot_filled == 0
    is_new_mode_slot = mode_slot_filled == 0

    return is_new_band_slot or is_new_mode_slot


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
    """Check if QSOs would earn DXCC credit by filling unfilled slots.

    DXCC has two independent slot types:
    1. Band slots: (dxcc, band) - e.g., "10M + Bonaire"
    2. Mode slots: (dxcc, mode_group) - e.g., "Phone + Bonaire"

    A QSO is "unique" (earns credit) if it fills at least one unfilled slot.
    Only QSOs with app_lotw_credit_granted set count as filling slots.

    Returns dict mapping QSO id -> is_unique (True if fills any new slot).
    """
    if not qsos:
        return {}

    # Get all DXCC entities we need to check
    dxcc_values = {qso.dxcc for qso in qsos}

    # Query all user's CREDITED QSOs for these entities
    # Only credited QSOs count as filling slots
    stmt = (
        select(QSOReport.id, QSOReport.mode, QSOReport.dxcc, QSOReport.band)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.dxcc.in_(dxcc_values),
                QSOReport.app_lotw_credit_granted.isnot(None),
            )
        )
    )

    credited_qsos = session.execute(stmt).fetchall()

    # Build sets of filled slots (from credited QSOs only)
    filled_band_slots: set[tuple[str, str]] = set()  # (dxcc, band)
    filled_mode_slots: set[tuple[str, str]] = set()  # (dxcc, mode_group)

    for row in credited_qsos:
        _, mode, dxcc, band = row
        filled_band_slots.add((dxcc, band))
        filled_mode_slots.add((dxcc, _get_mode_group(mode)))

    # Check each QSO - unique if it fills ANY unfilled slot
    result = {}
    for qso in qsos:
        band_slot = (qso.dxcc, qso.band)
        mode_slot = (qso.dxcc, _get_mode_group(qso.mode))

        is_new_band_slot = band_slot not in filled_band_slots
        is_new_mode_slot = mode_slot not in filled_mode_slots

        # Unique if EITHER slot is new
        result[qso.id] = is_new_band_slot or is_new_mode_slot

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
