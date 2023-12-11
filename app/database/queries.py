from datetime import datetime

from sqlalchemy import Sequence, and_, func, select
from sqlalchemy.orm import Session

from .table_declarations import QSOReport, User


def get_object[T](type_: T, id: int, session: Session) -> T | None:
    return session.scalar(select(type_).where(type_.id == id))


def ensure_user(op: str, session: Session) -> User:
    user = session.scalar(select(User).where(User.op == op))

    if not user:
        user = User(op=op)

    return user


def get_user(op: str, session: Session) -> User:
    user = session.scalar(select(User).where(User.op == op))

    if not user:
        raise ValueError(f"No user with op={op} found!")

    return user


def qso_report_exists(
    app_lotw_qso_timestamp: datetime, session: Session
) -> bool:
    return bool(
        session.scalar(
            select(QSOReport).where(
                QSOReport.app_lotw_qso_timestamp == app_lotw_qso_timestamp
            )
        )
    )


def get_most_recent_rxqsls(user: User, session: Session) -> Sequence[QSOReport]:
    stmt = (
        select(QSOReport)
        .join(User)
        .order_by(QSOReport.app_lotw_rxqsl.desc())
        .limit(25)
    )

    return session.scalars(stmt).all()


def get_user_qsos_by_rxqso(user: User, session: Session) -> Sequence[QSOReport]:
    stmt = (
        select(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.latitude != None,
                QSOReport.longitude != None,
            )
        )
        .order_by(QSOReport.app_lotw_rxqsl.desc())
    )

    return session.scalars(stmt).all()


def get_user_qsos_for_map_by_rxqso(
    user: User,
    session: Session,
) -> list[tuple]:
    stmt = (
        select(
            QSOReport.id,
            QSOReport.gridsquare,
            QSOReport.latitude,
            QSOReport.longitude,
            QSOReport.call,
            QSOReport.band,
            QSOReport.mode,
            QSOReport.app_lotw_qso_timestamp,
        )
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.latitude != None,
                QSOReport.longitude != None,
            )
        )
        .order_by(QSOReport.app_lotw_rxqsl.desc())
    )

    return session.execute(statement=stmt).all()


def get_user_qsos_for_map_by_rxqso_count(
    user: User,
    session: Session,
) -> int:
    stmt = (
        select(func.count())
        .select_from(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.latitude != None,
                QSOReport.longitude != None,
            )
        )
    )

    return session.scalar(statement=stmt)
