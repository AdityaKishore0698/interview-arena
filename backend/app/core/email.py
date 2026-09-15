"""Minimal transactional email sender.

Uses plain SMTP (stdlib `smtplib`) so it works with any provider that
exposes SMTP credentials (Gmail App Passwords, SendGrid, Mailgun, Resend,
your own mail server, ...) without adding a vendor-specific dependency.

If SMTP isn't configured (no SMTP_HOST), calls fall back to printing the
email to the console — this is the existing local-dev behavior and keeps
`TESTING=true` / no-env-vars workflows unaffected.
"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from .config import settings

logger = logging.getLogger(__name__)


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(msg["From"], [to], msg.as_string())


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Returns True if actually sent, False if it just logged
    (SMTP not configured) or failed — callers should not treat a False return
    as fatal since the caller-facing flow (OTP, password reset, ...) must
    never leak whether delivery succeeded, to avoid account enumeration.
    """
    if not settings.SMTP_HOST:
        # No mail server configured (local dev / TESTING). Preserve the
        # original developer-visible behavior instead of failing silently.
        logger.info("SMTP not configured; printing email instead.\nTo: %s\nSubject: %s\n%s", to, subject, body)
        print(f"[email:{subject}] to={to}\n{body}")
        return False

    try:
        await asyncio.to_thread(_send_sync, to, subject, body)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False
