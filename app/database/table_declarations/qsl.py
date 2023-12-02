from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QSL(Base):
    __tablename__ = "qsls"

    id: Mapped[int] = mapped_column(primary_key=True)
    op: Mapped[str]
    worked: Mapped[str]
    band: Mapped[str]
    mode: Mapped[str]
    details: Mapped[str]

    def __init__(
        self,
        op: str,
        worked: str,
        band: str,
        mode: str,
        details: str,
    ):
        self.op = op
        self.worked = worked
        self.band = band
        self.mode = mode
        self.details = details
        super().__init__()

    def __eq__(self, __value: object) -> bool:
        return super().__eq__(__value)
