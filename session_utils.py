import base64
import struct


class SessionStringError(ValueError):
    """Raised when USER_SESSION cannot be parsed as a valid session string."""


def _is_bot_token(raw: str) -> bool:
    return ":" in raw


def load_session_string(raw: str, api_id: int) -> str:
    """
    Validate and normalize a Pyrogram/PyroFork v2 session string.

    Returns the cleaned string that PyroFork can consume. Raises
    SessionStringError with a clear message when the value is missing,
    is a bot token, is not valid base64, or decodes to an unexpected size.
    """
    if not raw:
        raise SessionStringError(
            "USER_SESSION is missing or empty. Generate a Pyrogram v2 string session "
            "with @SMD_StringBot and set it in the USER_SESSION environment variable."
        )

    cleaned = (raw or "").strip().strip('"\'')
    cleaned = "".join(cleaned.split())

    for prefix in ("pyrogram:", "pyrofork:", "session:"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    if _is_bot_token(cleaned):
        raise SessionStringError(
            "USER_SESSION looks like a BOT TOKEN (contains ':'), not a string session. "
            "This bot logs in as a user account. Generate a Pyrogram v2 string session "
            "with @SMD_StringBot and set it in USER_SESSION."
        )

    try:
        data = base64.urlsafe_b64decode(cleaned + "=" * (-len(cleaned) % 4))
    except ValueError:
        raise SessionStringError(
            "USER_SESSION is not valid base64. Regenerate a fresh Pyrogram v2 string "
            "session with @SMD_StringBot and update USER_SESSION."
        ) from None

    new_size = struct.calcsize(">BI?256sQ?")   # 271 - current PyroFork format
    old_32 = struct.calcsize(">B?256sI?")       # 263 - legacy format
    old_64 = struct.calcsize(">B?256sQ?")       # 267 - legacy 64-bit format

    if len(data) not in (new_size, old_32, old_64):
        raise SessionStringError(
            f"USER_SESSION is corrupted: decoded to {len(data)} bytes, expected "
            f"{new_size} (or legacy {old_32}/{old_64}). It may be truncated, wrapped "
            "in quotes, or from a different library. Regenerate a fresh Pyrogram v2 "
            "string session with @SMD_StringBot and update USER_SESSION."
        )

    if len(data) == new_size:
        sid_api_id = struct.unpack(">BI?256sQ?", data)[1]
        if api_id and sid_api_id != api_id:
            raise SessionStringError(
                f"USER_SESSION was created for API_ID {sid_api_id}, but the config "
                f"uses API_ID {api_id}. Generate the string session with the same "
                "API_ID/API_HASH and update USER_SESSION."
            )

    return cleaned
