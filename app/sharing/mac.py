import shutil
import subprocess
from pathlib import Path

from app.sharing.base import ShareResult, SharingBackend

_SEND_EMAIL_SCRIPT = """
on run argv
  set theRecipient to item 1 of argv
  set theSubject to item 2 of argv
  set theBody to item 3 of argv
  set theAttachment to item 4 of argv
  tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:theSubject, content:theBody & return & return, visible:false}
    tell newMessage
      make new to recipient at end of to recipients with properties {address:theRecipient}
      make new attachment with properties {file name:(POSIX file theAttachment)} at after last paragraph
    end tell
    send newMessage
  end tell
end run
"""

_SEND_IMESSAGE_SCRIPT = """
on run argv
  set theRecipient to item 1 of argv
  set theMessage to item 2 of argv
  set theAttachment to item 3 of argv
  tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy theRecipient of targetService
    send (POSIX file theAttachment) to targetBuddy
    if theMessage is not "" then
      send theMessage to targetBuddy
    end if
  end tell
end run
"""

RECIPE_SHARE_DIR = Path.home() / "Pictures" / "RecipeShare"


def _run_osascript(script, args, timeout=60):
    result = subprocess.run(
        ["osascript", "-e", script, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        return ShareResult(False, result.stderr.strip() or "osascript failed")
    return ShareResult(True, "Sent.")


class MacSharingBackend(SharingBackend):
    def supports_email(self):
        return True

    def supports_imessage(self):
        return True

    def send_email(self, to, subject, body, attachment_path):
        try:
            return _run_osascript(
                _SEND_EMAIL_SCRIPT, [to, subject, body or "", str(attachment_path)]
            )
        except subprocess.TimeoutExpired:
            return ShareResult(False, "Mail.app did not respond in time.")
        except Exception as exc:
            return ShareResult(False, str(exc))

    def send_imessage(self, to, body, attachment_path):
        # Messages can silently fail to send attachments from arbitrary
        # paths; copying into ~/Pictures/RecipeShare/ first works around it.
        try:
            RECIPE_SHARE_DIR.mkdir(parents=True, exist_ok=True)
            local_copy = RECIPE_SHARE_DIR / Path(attachment_path).name
            shutil.copyfile(attachment_path, local_copy)
            return _run_osascript(_SEND_IMESSAGE_SCRIPT, [to, body or "", str(local_copy)])
        except subprocess.TimeoutExpired:
            return ShareResult(False, "Messages did not respond in time.")
        except Exception as exc:
            return ShareResult(False, str(exc))
