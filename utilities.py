from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.table_declarations import User


def logged_in(request: Request) -> bool:
    return request.session.get("logged_in", False)


def get_user(request: Request, session: Session) -> User:
    username = request.session.get("username", None)
    if username is None:
        raise ValueError

    user = session.scalar(select(User).where(User.mobile_lotw_username == username))

    if user is None:
        raise ValueError

    return user
