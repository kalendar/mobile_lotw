from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QSLEmail(Base):
    __tablename__ = "qsl_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    op: Mapped[str]
    worked: Mapped[str]
    band: Mapped[str]
    mode: Mapped[str]
    details: Mapped[str]

    def __init__(
        self,
        id: int,
        op: str,
        worked: str,
        band: str,
        mode: str,
        details: str,
    ):
        self.id = id
        self.op = op
        self.worked = worked
        self.band = band
        self.mode = mode
        self.details = details
        super().__init__()
