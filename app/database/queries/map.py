from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..table_declarations import QSOReport, User


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
                QSOReport.latitude.is_not(None),
                QSOReport.longitude.is_not(None),
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
                QSOReport.latitude.is_not(None),
                QSOReport.longitude.is_not(None),
            )
        )
    )

    return session.scalar(statement=stmt)
