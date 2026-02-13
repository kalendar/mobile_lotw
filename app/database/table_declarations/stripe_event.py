from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(index=True, unique=True)
    event_type: Mapped[str]
    status: Mapped[str] = mapped_column(default="received")
    payload: Mapped[dict[str, Any] | None]
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
