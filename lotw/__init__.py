from database.table_declarations.user import User
from env import SETTINGS
from lotw.auth import login
from lotw.qsls import retrieve_qsls


def update_user(user: User) -> None:
    """
    Assumes open session on User object.
    """
    cookies = login(
        username=user.lotw_username,
        password=user.get_lotw_password(database_key=SETTINGS.database_key),
    )

    user.set_lotw_cookies(cookies=cookies, database_key=SETTINGS.database_key)

    previous_qsls = user.qsl_reports
    current_qsls = retrieve_qsls(user=user)

    for current_qso in current_qsls:
        for previous_qso in previous_qsls:
            if current_qso == previous_qso:
                current_qso.notified = previous_qso.notified
                break

    user.qsl_reports = []
    user.qsl_reports.extend(current_qsls)
