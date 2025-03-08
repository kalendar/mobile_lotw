from typing import Type

from bs4 import BeautifulSoup
from requests import Response
from requests import get as r_get


def is_valid_response(response: Response) -> bool:
    if not response:
        return False

    text_response = (
        response.text if response.text else str(response.content, encoding="utf8")
    )

    return "postcard" not in text_response


def get(url: str, cookies: dict[str, str] | None) -> Response:
    response = r_get(url, cookies=cookies)

    if is_valid_response(response):
        return response
    else:
        raise ValueError


def convert_table[T](text: str, record_type: Type[T]) -> list[T]:
    result: list[T] = list()

    soup = BeautifulSoup(text, features="html.parser")

    trs = soup.select('form[action="qsos"] tr')[3:28]

    trs = soup.select("#accountStatusTable > tbody > tr")

    for tr in trs:
        tds = tr.select("td")

        result.append(record_type(*[td.text.strip() for td in tds]))

    return result
