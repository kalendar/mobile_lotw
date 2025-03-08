from bs4 import BeautifulSoup
from requests import get

from database.table_declarations.qso_report import QSLReport
from database.table_declarations.user import User
from env import SETTINGS
from lotw.util import is_valid_response


def retrieve_qsls(user: User) -> list[QSLReport]:
    qso_reports: list[QSLReport] = []

    response = get(
        SETTINGS.QSO_url,
        cookies=user.get_lotw_cookies(SETTINGS.database_key),
    )

    if is_valid_response(response):
        soup = BeautifulSoup(
            response.content.decode(encoding="utf-8"), features="html.parser"
        )

        trs = soup.select('form[action="qsos"] tr')[3:28]

        for tr in trs:
            tds = tr.select("td")

            qso_reports.append(
                QSLReport(
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
