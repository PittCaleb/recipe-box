class ShareResult:
    def __init__(self, success, message):
        self.success = success
        self.message = message


class SharingBackend:
    """Interface for sending a recipe by email or iMessage. Concrete
    backends implement whichever of these they can actually do; the UI
    hides a button when its backend reports it unsupported."""

    def supports_email(self):
        return False

    def supports_imessage(self):
        return False

    def send_email(self, to, subject, body, attachment_path):
        raise NotImplementedError

    def send_imessage(self, to, body, attachment_path):
        raise NotImplementedError
