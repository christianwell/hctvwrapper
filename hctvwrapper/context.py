from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot
    from .models import Author, Message


class Context:
    """Command context, similar to Pycord's ``commands.Context``."""

    def __init__(self, message: Message, bot: Bot) -> None:
        self.message: Message = message
        self.bot: Bot = bot

    @property
    def author(self) -> Author:
        return self.message.author

    @property
    def channel(self) -> str:
        return self.message.channel

    @property
    def content(self) -> str:
        return self.message.content

    async def reply(self, content: str) -> None:
        """Send a message mentioning the author, e.g. ``@user hello``."""
        await self.bot.send(f"@{self.author.username} {content}", channel=self.channel)

    async def send(self, content: str) -> None:
        """Send a message to the same channel without a mention."""
        await self.bot.send(content, channel=self.channel)

    async def delete(self) -> None:
        """Delete the triggering message (requires moderation permissions)."""
        if self.message.msg_id:
            await self.bot.delete_message(self.channel, self.message.msg_id)
