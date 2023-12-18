from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session

from ..table_declarations import QSOReport, User


def get_25_most_recent_rxqsls(
    user: User, session: Session
) -> Sequence[QSOReport]:
    stmt = (
        select(QSOReport)
        .join(User)
        .where(User.id == user.id)
        .order_by(QSOReport.app_lotw_rxqsl.desc())
        .limit(25)
    )

    return session.scalars(stmt).all()
