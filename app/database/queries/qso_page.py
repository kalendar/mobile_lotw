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
        .where(QSOReport.app_lotw_rxqsl.is_not(None))
        .order_by(QSOReport.app_lotw_rxqsl.desc(), QSOReport.id.desc())
        .limit(250)
    )
    rows = session.scalars(stmt).all()
    unique_rows: list[QSOReport] = []
    seen_keys: set[tuple] = set()
    for row in rows:
        key = (row.app_lotw_qso_timestamp, row.call)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_rows.append(row)
        if len(unique_rows) >= 25:
            break

    return unique_rows
