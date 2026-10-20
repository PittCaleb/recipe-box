import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9()\-.\s]{7,20}$")


def validate_email(value):
    value = (value or "").strip()
    if _EMAIL_RE.match(value):
        return value
    return None


def validate_imessage_target(value):
    """An iMessage target is either an email address or a phone number."""
    value = (value or "").strip()
    if _EMAIL_RE.match(value):
        return value
    if _PHONE_RE.match(value) and len(re.sub(r"\D", "", value)) >= 7:
        return value
    return None
