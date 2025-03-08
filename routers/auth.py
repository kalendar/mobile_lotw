from typing import Annotated

import starlette.status as status
from argon2 import PasswordHasher
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from database.table_declarations import User
from dependencies import SessionBeginDep, SessionDep
from env import SETTINGS

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "title": "Login"}
    )


@router.post("/login", response_class=RedirectResponse)
async def login_post(
    request: Request,
    mobile_lotw_username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: SessionDep,
):
    ph = PasswordHasher()

    user = session.scalar(
        select(User).where(User.mobile_lotw_username == mobile_lotw_username)
    )

    if user and ph.verify(user.password_hash, password):
        request.session["logged_in"] = True
        request.session["username"] = mobile_lotw_username

        return RedirectResponse(
            request.url_for("qsls"),
            status_code=status.HTTP_302_FOUND,
        )
    else:
        return HTMLResponse("Failed login")


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    request.session["logged_in"] = False
    request.session.pop("username", None)

    return RedirectResponse(
        request.url_for("index"),
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "title": "Register"}
    )


@router.post("/register")
async def register_post(
    request: Request,
    email: Annotated[str, Form()],
    mobile_lotw_username: Annotated[str, Form()],
    mobile_lotw_password: Annotated[str, Form()],
    lotw_username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: SessionBeginDep,
):
    existing_user = session.scalar(
        select(User).where(User.mobile_lotw_username == mobile_lotw_username)
    )
    if existing_user:
        return {"User already exists."}
    else:
        new_user = User(
            mobile_lotw_username=mobile_lotw_username,
            mobile_lotw_password=mobile_lotw_password,
            lotw_username=lotw_username,
            email=email,
        )

        new_user.set_lotw_password(password, SETTINGS.database_key)

        session.add(new_user)

        return RedirectResponse(
            request.url_for("index"),
            status_code=status.HTTP_302_FOUND,
        )
