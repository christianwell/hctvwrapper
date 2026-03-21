"""hctvwrapper — A Pycord-style Python wrapper for hackclub.tv."""

from .bot import Bot
from .context import Context
from .models import (
    Author,
    ChatAccess,
    Message,
    ModerationError,
    ModerationEvent,
    ModerationSettings,
    Permissions,
    Restriction,
    Session,
    SystemMessage,
)

__version__ = "0.1.0"
__all__ = [
    "Bot",
    "Context",
    "Author",
    "ChatAccess",
    "Message",
    "ModerationError",
    "ModerationEvent",
    "ModerationSettings",
    "Permissions",
    "Restriction",
    "Session",
    "SystemMessage",
]
