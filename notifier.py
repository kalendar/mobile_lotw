from typing import TYPE_CHECKING

from lotw import update_user

if TYPE_CHECKING:
    from database.table_declarations import User


def notify_user(user: User):
    for qso in user.qso_reports:
        if not qso.notified:
            print(f"Notify for: {qso.user.id}, {qso.datetime}, {qso.worked}")
            qso.notified = True


def update_and_notify_user(user: User):
    """
    Assumes open, committing session
    """

    update_user(user=user)
    notify_user(user=user)
