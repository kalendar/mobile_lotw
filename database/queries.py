from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from table_declarations import QSLReport, User


def get_unnotified_qsos(user: User, session: Session) -> Sequence[QSLReport]:
    qsos = session.scalars(
        select(QSLReport)
        .where(QSLReport.user == user)
        .where(QSLReport.notified == False)  # noqa: E712
    )

    return qsos.all()
