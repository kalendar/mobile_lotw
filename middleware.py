import starlette.status as status
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

UNAUTHENTICATED_ROUTES = [
    "/",
    "/about",
    "/privacy",
    "/login",
    "/logout",
    "/register",
]


class AuthenticatedRoutes(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        # Skip checking for unauthenticated routes
        if request.url.path in UNAUTHENTICATED_ROUTES:
            return await call_next(request)

        if "session" not in request.scope:
            raise RuntimeError("SessionMiddleware did not process this request!")

        logged_in = request.session.get("logged_in", False)

        if logged_in:
            return await call_next(request)
        else:
            return RedirectResponse(
                url=request.url_for("login"),
                status_code=status.HTTP_302_FOUND,
            )
