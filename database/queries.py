from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from table_declarations import QSOReport, User


def get_unnotified_qsos(user: User, session: Session) -> Sequence[QSOReport]:
    qsos = session.scalars(
        select(QSOReport)
        .where(QSOReport.user == user)
        .where(QSOReport.notified == False)  # noqa: E712
    )

    return qsos.all()
