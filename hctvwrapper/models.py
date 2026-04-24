from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Author:
    id: str
    username: str
    pfp_url: str | None = None
    display_name: str | None = None
    is_bot: bool = False
    is_platform_admin: bool = False
    channel_role: str | None = None  # owner / manager / chatModerator / botModerator

    def __str__(self) -> str:
        return self.display_name or self.username

    @property
    def is_owner(self) -> bool:
        return self.channel_role == "owner"

    @property
    def is_manager(self) -> bool:
        return self.channel_role == "manager"

    @property
    def is_moderator(self) -> bool:
        return self.channel_role in ("chatModerator", "botModerator")

    @property
    def is_staff(self) -> bool:
        """True if the user is owner, manager, or any kind of moderator."""
        return self.channel_role in ("owner", "manager", "chatModerator", "botModerator")

    def has_role(self, *roles: str) -> bool:
        """Check if the user has any of the given roles.

        Example::

            if ctx.author.has_role("owner", "manager"):
                ...
        """
        return self.channel_role in roles


@dataclass
class Message:
    content: str
    author: Author
    channel: str
    msg_id: str | None = None
    timestamp: float = 0.0
    type: str = "message"  # "message" or "systemMsg"

    @property
    def is_bot(self) -> bool:
        return self.author.is_bot


@dataclass
class Permissions:
    can_moderate: bool = False


@dataclass
class ModerationSettings:
    has_blocked_terms: bool = False
    slow_mode_seconds: int = 0
    max_message_length: int = 400


@dataclass
class Session:
    viewer: Author | None = None
    permissions: Permissions = field(default_factory=Permissions)
    moderation: ModerationSettings = field(default_factory=ModerationSettings)


@dataclass
class SystemMessage:
    type: str  # connected / disconnected / error
    channel: str
    content: str
    timestamp: float = 0.0


@dataclass
class Restriction:
    type: str  # timeout / ban
    reason: str | None = None
    expires_at: str | None = None


@dataclass
class ChatAccess:
    can_send: bool = True
    restriction: Restriction | None = None


@dataclass
class ModerationError:
    code: str
    message: str
    restriction: Restriction | None = None


@dataclass
class ModerationEvent:
    type: str  # messageDeleted
    msg_id: str
    channel: str
