from __future__ import annotations

import asyncio
import inspect
import logging
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from .connection import (
    ConnectionManager,
    parse_chat_access,
    parse_message,
    parse_moderation_error,
    parse_moderation_event,
    parse_session,
)
from .context import Context
from .models import Session

log = logging.getLogger("hctvwrapper")


@dataclass
class Command:
    name: str
    callback: Callable[..., Coroutine[Any, Any, None]]
    aliases: list[str] = field(default_factory=list)


class Bot:
    """Pycord-style bot for hackclub.tv chat.

    Example::

        bot = Bot(command_prefix="!")

        @bot.event
        async def on_ready(session):
            print("Connected!")

        @bot.command()
        async def ping(ctx):
            await ctx.reply("pong!")

        bot.run("hctvb_xxx", channel="bot-playground")
    """

    def __init__(
        self,
        command_prefix: str = "!",
        *,
        auto_reconnect: bool = True,
        reconnect_max_attempts: int = 0,
    ) -> None:
        self.command_prefix = command_prefix
        self.session: Session | None = None

        self._auto_reconnect = auto_reconnect
        self._reconnect_max_attempts = reconnect_max_attempts
        self._connection: ConnectionManager | None = None
        self._events: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}
        self._commands: dict[str, Command] = {}
        self._ready_fired = False

    # -- decorators -----------------------------------------------------------

    def event(self, func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., Coroutine[Any, Any, None]]:
        """Register an event handler.

        Supported events:
            on_ready, on_message, on_history, on_system_message,
            on_message_deleted, on_chat_access, on_moderation_error,
            on_disconnect, on_reconnect, on_error
        """
        self._events[func.__name__] = func
        return func

    def command(
        self,
        name: str | None = None,
        aliases: list[str] | None = None,
    ) -> Callable[[Callable[..., Coroutine[Any, Any, None]]], Callable[..., Coroutine[Any, Any, None]]]:
        """Register a prefix command.

        Example::

            @bot.command()
            async def ping(ctx):
                await ctx.reply("pong!")

            @bot.command(name="say", aliases=["echo"])
            async def say_cmd(ctx, *, text):
                await ctx.reply(text)
        """

        def decorator(func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., Coroutine[Any, Any, None]]:
            cmd_name = name or func.__name__
            cmd = Command(name=cmd_name, callback=func, aliases=aliases or [])
            self._commands[cmd_name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd
            return func

        return decorator

    # -- public api -----------------------------------------------------------

    async def send(self, content: str, channel: str | None = None) -> None:
        """Send a message to a channel."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        await self._connection.send_message(content, channel)

    async def delete_message(self, channel: str, msg_id: str) -> None:
        """Delete a message by ID (requires moderation permissions)."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        await self._connection.send_json(
            {"type": "mod:deleteMessage", "msgId": msg_id}, channel
        )

    async def timeout_user(
        self,
        channel: str,
        user_id: str,
        duration: int = 300,
        reason: str | None = None,
    ) -> None:
        """Timeout a user (10–86400 seconds)."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        payload: dict[str, Any] = {
            "type": "mod:timeoutUser",
            "targetUserId": user_id,
            "durationSeconds": duration,
        }
        if reason:
            payload["reason"] = reason
        await self._connection.send_json(payload, channel)

    async def ban_user(
        self,
        channel: str,
        user_id: str,
        reason: str | None = None,
    ) -> None:
        """Permanently ban a user."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        payload: dict[str, Any] = {
            "type": "mod:banUser",
            "targetUserId": user_id,
        }
        if reason:
            payload["reason"] = reason
        await self._connection.send_json(payload, channel)

    async def lift_timeout(self, channel: str, user_id: str) -> None:
        """Remove a timeout from a user."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        await self._connection.send_json(
            {"type": "mod:liftTimeout", "targetUserId": user_id}, channel
        )

    async def unban_user(self, channel: str, user_id: str) -> None:
        """Unban a user."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        await self._connection.send_json(
            {"type": "mod:unbanUser", "targetUserId": user_id}, channel
        )

    async def lookup_emojis(self, names: list[str], channel: str | None = None) -> None:
        """Request emoji URL lookups. Results arrive via on_emoji_response."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        conn = self._connection._get_connection(channel)
        await conn.send_json({"type": "emojiMsg", "emojis": names})

    async def search_emojis(self, term: str, channel: str | None = None) -> None:
        """Search for emojis. Results arrive via on_emoji_search."""
        if not self._connection:
            raise RuntimeError("Bot is not connected")
        conn = self._connection._get_connection(channel)
        await conn.send_json({"type": "emojiSearch", "searchTerm": term})

    @property
    def connected_channels(self) -> list[str]:
        if not self._connection:
            return []
        return self._connection.connected_channels

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected

    def is_connected_to(self, channel: str) -> bool:
        if not self._connection:
            return False
        return self._connection.is_connected_to(channel)

    # -- run ------------------------------------------------------------------

    def run(
        self,
        token: str,
        channel: str | None = None,
        channels: list[str] | None = None,
    ) -> None:
        """Blocking entry point — starts the bot and runs forever.

        Args:
            token: Bot API key (``hctvb_xxx``).
            channel: Single channel to connect to.
            channels: List of channels to connect to.
        """
        asyncio.run(self.start(token, channel=channel, channels=channels))

    async def start(
        self,
        token: str,
        channel: str | None = None,
        channels: list[str] | None = None,
    ) -> None:
        """Async entry point — use this if you manage your own event loop."""
        channel_list = channels or ([channel] if channel else [])
        if not channel_list:
            raise ValueError("Provide at least one channel via channel= or channels=")

        self._ready_fired = False
        self._connection = ConnectionManager(
            token,
            auto_reconnect=self._auto_reconnect,
            reconnect_max_attempts=self._reconnect_max_attempts,
        )
        self._connection._on_disconnect = self._handle_disconnect
        self._connection._on_reconnect = self._handle_reconnect

        for ch in channel_list:
            await self._connection.connect(ch, self._dispatch)

        await self._connection.wait()

    async def close(self) -> None:
        """Gracefully disconnect from all channels and stop the bot."""
        if self._connection:
            await self._connection.close()

    async def _handle_disconnect(self, channel: str) -> None:
        await self._fire("on_disconnect", channel)

    async def _handle_reconnect(self, channel: str) -> None:
        await self._fire("on_reconnect", channel)

    # -- internal dispatch ----------------------------------------------------

    async def _dispatch(self, channel: str, data: dict[str, Any]) -> None:
        msg_type = data.get("type")

        if msg_type == "pong":
            return

        if msg_type == "session":
            self.session = parse_session(data)
            if not self._ready_fired:
                self._ready_fired = True
                await self._fire("on_ready", self.session)
            return

        if msg_type == "history":
            messages = [
                parse_message(m, channel) for m in data.get("messages", [])
            ]
            await self._fire("on_history", messages)
            return

        if msg_type == "message":
            message = parse_message(data, channel)
            await self._fire("on_message", message)
            await self._process_commands(message)
            return

        if msg_type == "chatAccess":
            access = parse_chat_access(data)
            await self._fire("on_chat_access", access, channel)
            return

        if msg_type == "systemMsg":
            from .models import SystemMessage
            import time

            sys_msg = SystemMessage(
                type="system",
                channel=channel,
                content=data.get("message", ""),
                timestamp=time.time(),
            )
            await self._fire("on_system_message", sys_msg)
            return

        if msg_type == "moderationError":
            error = parse_moderation_error(data)
            await self._fire("on_moderation_error", error, channel)
            return

        if msg_type == "messageDeleted":
            event = parse_moderation_event(data, channel)
            await self._fire("on_message_deleted", event)
            return

        if msg_type == "emojiMsgResponse":
            await self._fire("on_emoji_response", data.get("emojis", {}))
            return

        if msg_type == "emojiSearchResponse":
            await self._fire("on_emoji_search", data.get("results", []))
            return

    async def _fire(self, event_name: str, *args: Any) -> None:
        handler = self._events.get(event_name)
        if handler:
            try:
                await handler(*args)
            except Exception as exc:
                log.exception("Error in event handler %s", event_name)
                await self._fire_error(event_name, exc)

    async def _fire_error(self, source: str, exc: Exception) -> None:
        """Invoke on_error if registered, without recursing."""
        handler = self._events.get("on_error")
        if handler:
            try:
                await handler(source, exc)
            except Exception:
                log.exception("Error in on_error handler")

    async def _process_commands(self, message: 'Message') -> None:
        if not message.content.startswith(self.command_prefix):
            return

        # Don't respond to own messages
        if message.author.is_bot and self.session and self.session.viewer:
            if message.author.username == self.session.viewer.username:
                return

        content = message.content[len(self.command_prefix) :]
        if not content:
            return

        parts = content.split(None, 1)
        cmd_name = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        cmd = self._commands.get(cmd_name)
        if not cmd:
            return

        ctx = Context(message, self)

        try:
            # Inspect the callback signature to determine how to pass args
            sig = inspect.signature(cmd.callback)
            params = list(sig.parameters.values())

            # First param is always ctx
            params = params[1:]  # skip ctx

            if not params:
                await cmd.callback(ctx)
            elif any(p.kind == inspect.Parameter.KEYWORD_ONLY for p in params):
                # *, text style — pass the entire rest as a keyword arg
                kw_param = next(p for p in params if p.kind == inspect.Parameter.KEYWORD_ONLY)
                await cmd.callback(ctx, **{kw_param.name: rest})
            else:
                # Positional args — split by whitespace
                try:
                    args = shlex.split(rest) if rest else []
                except ValueError:
                    args = rest.split() if rest else []

                # Check required arg count
                required = sum(
                    1
                    for p in params
                    if p.default is inspect.Parameter.empty
                    and p.kind
                    in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                )
                if len(args) < required:
                    names = [p.name for p in params[:required]]
                    await ctx.reply(f"missing arguments: {', '.join(names[len(args):])}")
                    return

                await cmd.callback(ctx, *args)
        except Exception as exc:
            log.exception("Error in command %s", cmd.name)
            await self._fire_error(f"command:{cmd.name}", exc)
