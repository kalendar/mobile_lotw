import smtplib
from email.mime.text import MIMEText

from database.table_declarations import User
from env import SETTINGS
from lotw import update_user


def notify_user(user: User):
    """
    Assumes open, committing session to update notification status
    """

    body = ""

    for qso in user.qso_reports:
        if not qso.notified:
            body += f"You worked {qso.worked} on {qso.datetime}.\n"
            print(f"Notified for: {qso.user.id}, {qso.datetime}, {qso.worked}")
            qso.notified = True

    if body != "":
        sender = SETTINGS.email_settings.sender_address
        recipient = user.email
        body += "\nhttps://mobilelotw.org/qsls"

        msg = MIMEText(body)
        msg["Subject"] = "New QSLs"
        msg["From"] = sender
        msg["To"] = recipient

        try:
            with smtplib.SMTP(
                SETTINGS.email_settings.SMTP_address, SETTINGS.email_settings.SMTP_port
            ) as smtp_server:
                smtp_server.sendmail(sender, recipient, msg.as_string())
            print("Message sent!")
        except Exception as e:
            print(f"Failed to send the email. Error: {e}")


def update_and_notify_user(user: User):
    """
    Assumes open, committing session
    """

    update_user(user=user)
    notify_user(user=user)
