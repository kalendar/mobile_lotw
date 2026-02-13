from sqlalchemy import Sequence, and_, func, select
from sqlalchemy.orm import Session

from ..table_declarations import QSOReport, User


def callsign(user: User, query: str, session: Session) -> Sequence[QSOReport]:
    normalized = (query or "").strip()
    wildcard_query = f"%{normalized}%"
    stmt = (
        select(QSOReport)
        .join(User)
        .where(
            and_(
                User.id == user.id,
                QSOReport.call.ilike(wildcard_query),
            )
        )
        .order_by(QSOReport.app_lotw_rxqsl.desc())
        .limit(100)
    )

    return session.scalars(stmt).all()
