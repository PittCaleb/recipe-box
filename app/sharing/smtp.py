import os
import smtplib
from email.message import EmailMessage

from app.sharing.base import ShareResult, SharingBackend


class SmtpSharingBackend(SharingBackend):
    """Email via a configured SMTP relay, for the future NAS deployment.
    Reads RECIPES_SMTP_HOST / _PORT / _USER / _PASSWORD / _FROM from the
    environment. iMessage has no NAS equivalent, so that button stays hidden."""

    def supports_email(self):
        return bool(os.environ.get("RECIPES_SMTP_HOST"))

    def supports_imessage(self):
        return False

    def send_email(self, to, subject, body, attachment_path):
        host = os.environ.get("RECIPES_SMTP_HOST")
        if not host:
            return ShareResult(False, "SMTP is not configured on this server.")

        port = int(os.environ.get("RECIPES_SMTP_PORT", "587"))
        user = os.environ.get("RECIPES_SMTP_USER")
        password = os.environ.get("RECIPES_SMTP_PASSWORD")
        sender = os.environ.get("RECIPES_SMTP_FROM", user or "recipes@localhost")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to
        msg.set_content(body or "")

        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype="application", subtype="pdf",
                filename=str(attachment_path).rsplit("/", 1)[-1],
            )

        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
            return ShareResult(True, "Sent.")
        except Exception as exc:
            return ShareResult(False, str(exc))

    def send_imessage(self, to, body, attachment_path):
        return ShareResult(False, "iMessage isn't available on this server.")
