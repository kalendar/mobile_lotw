from datetime import datetime

from sqlalchemy import and_, func, select
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
