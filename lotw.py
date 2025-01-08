from bs4 import BeautifulSoup
from requests import Response, get, post

from database.table_declarations.qso_report import QSOReport
from database.table_declarations.user import User
from env import SETTINGS


def login(username: str, password: str) -> dict[str, str]:
    lotw_payload = {
        "login": username.lower(),
        "password": password,
        "acct_sel": "",
        "thisForm": "login",
    }

    # Post to LOTW and save response
    login_response = post(url=SETTINGS.lotw_login_url, data=lotw_payload)

    # Check if login failed
    if not is_valid_response(response=login_response):
        raise ValueError

    key, value = login_response.headers.get("Set-Cookie").split(";")[0].split("=")  # type: ignore

    return {key: value}


def retrieve_qsos(user: User) -> list[QSOReport]:
    qso_reports: list[QSOReport] = []

    response = get(
        SETTINGS.QSO_url,
        cookies=user.get_lotw_cookies(SETTINGS.database_key),
    )

    soup = BeautifulSoup(
        response.content.decode(encoding="utf-8"), features="html.parser"
    )

    if is_valid_response(response):
        trs = soup.select('form[action="qsos"] tr')[3:28]

        for tr in trs:
            tds = tr.select("td")

            qso_reports.append(
                QSOReport(
                    user=user,
                    call_sign=tds[1].text,
                    worked=tds[2].text,
                    datetime=tds[3].text,
                    band=tds[4].text,
                    mode=tds[5].text,
                    frequency=tds[6].text,
                    qsl=tds[7].text.strip(),
                    challenge=bool(tds[-1].text.strip()),
                )
            )

        return qso_reports
    else:
        raise ValueError


def update_user(user: User) -> None:
    """
    Assumes open session on User object.
    """
    cookies = login(
        username=user.lotw_username,
        password=user.get_lotw_password(database_key=SETTINGS.database_key),
    )

    user.set_lotw_cookies(cookies=cookies, database_key=SETTINGS.database_key)

    previous_qsos = user.qso_reports
    current_qsos = retrieve_qsos(user=user)

    for current_qso in current_qsos:
        for previous_qso in previous_qsos:
            if current_qso == previous_qso:
                current_qso.notified = previous_qso.notified
                break

    user.qso_reports = []
    user.qso_reports.extend(current_qsos)


def is_valid_response(response: Response) -> bool:
    if not response:
        return False

    text_response = (
        response.text if response.text else str(response.content, encoding="utf8")
    )

    return "postcard" not in text_response
