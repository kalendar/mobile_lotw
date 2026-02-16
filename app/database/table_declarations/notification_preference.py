from datetime import datetime, time, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
    )
    user: Mapped["User"] = relationship(back_populates="notification_preference")

    qsl_digest_enabled: Mapped[bool] = mapped_column(default=False)
    qsl_digest_time_local: Mapped[time] = mapped_column(
        Time(),
        default=time(hour=8, minute=0),
    )
    qsl_digest_frequency: Mapped[str] = mapped_column(
        String(length=32),
        default="daily",
    )
    fallback_to_email: Mapped[bool] = mapped_column(default=True)
    use_account_email_for_notifications: Mapped[bool] = mapped_column(default=True)
    notification_email: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
    )
    quiet_hours_start_local: Mapped[time | None] = mapped_column(
        Time(),
        nullable=True,
    )
    quiet_hours_end_local: Mapped[time | None] = mapped_column(
        Time(),
        nullable=True,
    )
    last_digest_cursor_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )
