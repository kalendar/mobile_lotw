from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib

from flask import current_app

from ..database.table_declarations import QSLDigestBatch, User


class DigestEmailSendError(RuntimeError):
    pass


def _default_send_callable(message: EmailMessage) -> str:
    smtp_host = current_app.config.get("DIGEST_SMTP_HOST")
    smtp_port = current_app.config.get("DIGEST_SMTP_PORT", 587)
    smtp_user = current_app.config.get("DIGEST_SMTP_USERNAME")
    smtp_password = current_app.config.get("DIGEST_SMTP_PASSWORD")
    smtp_from = current_app.config.get("DIGEST_SMTP_FROM_EMAIL")
    use_starttls = current_app.config.get("DIGEST_SMTP_STARTTLS", True)

    if not smtp_host or not smtp_from:
        raise DigestEmailSendError("smtp_not_configured")

    with smtplib.SMTP(host=smtp_host, port=int(smtp_port), timeout=30) as client:
        if use_starttls:
            client.starttls()
        if smtp_user and smtp_password:
            client.login(user=smtp_user, password=smtp_password)
        client.send_message(message)

    # SMTP has no universal message id response, reuse generated Message-ID.
    return message.get("Message-Id", "")


def send_qsl_digest_email(
    *,
    user: User,
    batch: QSLDigestBatch,
    digest_url: str,
    recipient_email: str | None = None,
    send_callable=None,
) -> str:
    to_email = (recipient_email or user.email or "").strip()
    if not to_email:
        raise DigestEmailSendError("missing_recipient_email")

    sender = send_callable or _default_send_callable
    from_email = current_app.config.get("DIGEST_SMTP_FROM_EMAIL", "info@mobilelotw.org")

    msg = EmailMessage()
    msg["Subject"] = f"Daily QSL Digest: {batch.qsl_count} new QSLs"
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Date"] = datetime.now(tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg.set_content(
        "\n".join(
            [
                f"Hi {user.op},",
                "",
                f"You received {batch.qsl_count} new LoTW QSLs.",
                f"View your digest: {digest_url}",
                "",
                "73,",
                "Mobile LoTW",
            ]
        )
    )

    return sender(msg)
