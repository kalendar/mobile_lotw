from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class QSLReport(Base):
    __tablename__ = "qsl_reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship(back_populates="qsl_reports")

    call_sign: Mapped[str]
    worked: Mapped[str]
    datetime: Mapped[str]
    band: Mapped[str]
    mode: Mapped[str]
    frequency: Mapped[str]
    qsl: Mapped[str]
    challenge: Mapped[bool]
    notified: Mapped[bool] = mapped_column(default=False)

    def __init__(
        self,
        user: User,
        call_sign: str,
        worked: str,
        datetime: str,
        band: str,
        mode: str,
        frequency: str,
        qsl: str,
        challenge: bool,
    ):
        self.user_id = user.id
        self.user = user
        self.call_sign = call_sign
        self.worked = worked
        self.datetime = datetime
        self.band = band
        self.mode = mode
        self.frequency = frequency
        self.qsl = qsl
        self.challenge = challenge

    def __repr__(self):
        return f"{self.user_id}{self.datetime}{self.worked}{self.notified}"

    def __eq__(self, value: Any):
        if isinstance(value, QSLReport):
            return hash(f"{self.user_id}{self.datetime}{self.worked}") == hash(
                f"{value.user_id}{value.datetime}{value.worked}"
            )
        return False
