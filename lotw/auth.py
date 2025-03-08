from requests import post

from env import SETTINGS
from lotw.util import is_valid_response


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
