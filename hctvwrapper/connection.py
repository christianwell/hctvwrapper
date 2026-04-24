from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

import websockets
import websockets.asyncio.client

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

log = logging.getLogger("hctvwrapper")

DEFAULT_BASE_URL = "wss://hackclub.tv/api/stream/chat/ws"
PING_INTERVAL = 5  # seconds (Cloudflare requirement)
RECONNECT_BASE_DELAY = 1.0  # seconds
RECONNECT_MAX_DELAY = 60.0  # seconds
RECONNECT_MAX_ATTEMPTS = 0  # 0 = unlimited

Dispatcher = Callable[[str, Any], Coroutine[Any, Any, None]]
LifecycleCallback = Callable[[str], Coroutine[Any, Any, None]]


class ChannelConnection:
    def __init__(self, ws: websockets.asyncio.client.ClientConnection, channel: str):
        self.ws = ws
        self.channel = channel
        self._ping_task: asyncio.Task[None] | None = None
        self._recv_task: asyncio.Task[None] | None = None

    async def start(self, dispatcher: Dispatcher) -> None:
        self._ping_task = asyncio.create_task(self._ping_loop())
        self._recv_task = asyncio.create_task(self._recv_loop(dispatcher))

    async def _ping_loop(self) -> None:
        try:
            while True:
                await self.ws.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(PING_INTERVAL)
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    async def _recv_loop(self, dispatcher: Dispatcher) -> None:
        try:
            async for raw in self.ws:
                data = json.loads(raw)
                await dispatcher(self.channel, data)
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    async def send_json(self, payload: dict[str, Any]) -> None:
        await self.ws.send(json.dumps(payload))

    async def close(self) -> None:
        if self._ping_task:
            self._ping_task.cancel()
        if self._recv_task:
            self._recv_task.cancel()
        await self.ws.close()


class ConnectionManager:
    def __init__(
        self,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        auto_reconnect: bool = True,
        reconnect_max_attempts: int = RECONNECT_MAX_ATTEMPTS,
    ):
        self._token = token
        self._base_url = base_url
        self._auto_reconnect = auto_reconnect
        self._reconnect_max_attempts = reconnect_max_attempts
        self._connections: dict[str, ChannelConnection] = {}
        self._reconnect_tasks: dict[str, asyncio.Task[None]] = {}
        self._closing = False
        self._on_disconnect: LifecycleCallback | None = None
        self._on_reconnect: LifecycleCallback | None = None

    async def connect(self, channel: str, dispatcher: Dispatcher) -> None:
        if channel in self._connections:
            raise RuntimeError(f"Already connected to channel: {channel}")

        ws = await self._open_ws(channel)
        conn = ChannelConnection(ws, channel)
        self._connections[channel] = conn
        await conn.start(dispatcher)
        log.info("Connected to channel: %s", channel)

        # Wrap the recv task so we detect when it ends (disconnect)
        original_recv = conn._recv_task
        conn._recv_task = asyncio.create_task(
            self._watch_connection(channel, original_recv, dispatcher)
        )

    async def _open_ws(self, channel: str) -> websockets.asyncio.client.ClientConnection:
        url = f"{self._base_url}/{channel}"
        headers = {"Authorization": f"Bearer {self._token}"}
        return await websockets.asyncio.client.connect(url, additional_headers=headers)

    async def _watch_connection(
        self,
        channel: str,
        recv_task: asyncio.Task[None] | None,
        dispatcher: Dispatcher,
    ) -> None:
        """Wait for recv to end, then trigger reconnect if enabled."""
        if recv_task is None:
            return
        try:
            await recv_task
        except asyncio.CancelledError:
            return

        # Connection dropped
        log.warning("Disconnected from channel: %s", channel)
        self._connections.pop(channel, None)

        if self._on_disconnect:
            try:
                await self._on_disconnect(channel)
            except Exception:
                log.exception("Error in on_disconnect callback")

        if self._auto_reconnect and not self._closing:
            self._reconnect_tasks[channel] = asyncio.create_task(
                self._reconnect_loop(channel, dispatcher)
            )

    async def _reconnect_loop(self, channel: str, dispatcher: Dispatcher) -> None:
        delay = RECONNECT_BASE_DELAY
        attempts = 0
        while not self._closing:
            attempts += 1
            if self._reconnect_max_attempts and attempts > self._reconnect_max_attempts:
                log.error(
                    "Gave up reconnecting to %s after %d attempts", channel, attempts - 1
                )
                return

            log.info("Reconnecting to %s (attempt %d, delay %.1fs)...", channel, attempts, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)

            try:
                ws = await self._open_ws(channel)
            except Exception:
                log.warning("Reconnect to %s failed, retrying...", channel)
                continue

            conn = ChannelConnection(ws, channel)
            self._connections[channel] = conn
            await conn.start(dispatcher)
            log.info("Reconnected to channel: %s", channel)

            # Watch again
            original_recv = conn._recv_task
            conn._recv_task = asyncio.create_task(
                self._watch_connection(channel, original_recv, dispatcher)
            )

            self._reconnect_tasks.pop(channel, None)

            if self._on_reconnect:
                try:
                    await self._on_reconnect(channel)
                except Exception:
                    log.exception("Error in on_reconnect callback")
            return

    async def disconnect(self, channel: str | None = None) -> None:
        if channel:
            # Cancel any pending reconnect
            task = self._reconnect_tasks.pop(channel, None)
            if task:
                task.cancel()
            conn = self._connections.pop(channel, None)
            if conn:
                await conn.close()
        else:
            for task in self._reconnect_tasks.values():
                task.cancel()
            self._reconnect_tasks.clear()
            for conn in self._connections.values():
                await conn.close()
            self._connections.clear()

    async def close(self) -> None:
        """Gracefully shut down all connections and stop reconnecting."""
        self._closing = True
        await self.disconnect()

    async def send_message(self, content: str, channel: str | None = None) -> None:
        conn = self._get_connection(channel)
        await conn.send_json({"type": "message", "message": content})

    async def send_json(self, payload: dict[str, Any], channel: str) -> None:
        conn = self._get_connection(channel)
        await conn.send_json(payload)

    def _get_connection(self, channel: str | None = None) -> ChannelConnection:
        if channel:
            conn = self._connections.get(channel)
            if not conn:
                raise RuntimeError(f"Not connected to channel: {channel}")
            return conn
        if not self._connections:
            raise RuntimeError("Not connected to any channel")
        return next(iter(self._connections.values()))

    @property
    def connected_channels(self) -> list[str]:
        return list(self._connections.keys())

    @property
    def is_connected(self) -> bool:
        return len(self._connections) > 0

    def is_connected_to(self, channel: str) -> bool:
        return channel in self._connections

    async def wait(self) -> None:
        """Block until all connections are closed."""
        while not self._closing:
            tasks: list[asyncio.Task[None]] = []
            for conn in self._connections.values():
                if conn._recv_task:
                    tasks.append(conn._recv_task)
            for task in self._reconnect_tasks.values():
                tasks.append(task)
            if not tasks:
                break
            await asyncio.gather(*tasks, return_exceptions=True)


def parse_author(user: dict[str, Any]) -> Author:
    return Author(
        id=user.get("id", ""),
        username=user.get("username", ""),
        pfp_url=user.get("pfpUrl"),
        display_name=user.get("displayName"),
        is_bot=user.get("isBot", False),
        is_platform_admin=user.get("isPlatformAdmin", False),
        channel_role=user.get("channelRole"),
    )


def parse_message(data: dict[str, Any], channel: str) -> Message:
    return Message(
        content=data.get("message", ""),
        author=parse_author(data.get("user", {})),
        channel=channel,
        msg_id=data.get("msgId"),
        timestamp=time.time(),
        type=data.get("type", "message"),
    )


def parse_session(data: dict[str, Any]) -> Session:
    viewer_data = data.get("viewer")
    viewer = parse_author(viewer_data) if viewer_data else None

    perms_data = data.get("permissions", {})
    permissions = Permissions(can_moderate=perms_data.get("canModerate", False))

    mod_data = data.get("moderation", {})
    moderation = ModerationSettings(
        has_blocked_terms=mod_data.get("hasBlockedTerms", False),
        slow_mode_seconds=mod_data.get("slowModeSeconds", 0),
        max_message_length=mod_data.get("maxMessageLength", 400),
    )

    return Session(viewer=viewer, permissions=permissions, moderation=moderation)


def parse_restriction(data: dict[str, Any] | None) -> Restriction | None:
    if not data:
        return None
    return Restriction(
        type=data.get("type", ""),
        reason=data.get("reason"),
        expires_at=data.get("expiresAt"),
    )


def parse_chat_access(data: dict[str, Any]) -> ChatAccess:
    return ChatAccess(
        can_send=data.get("canSend", True),
        restriction=parse_restriction(data.get("restriction")),
    )


def parse_moderation_error(data: dict[str, Any]) -> ModerationError:
    return ModerationError(
        code=data.get("code", ""),
        message=data.get("message", ""),
        restriction=parse_restriction(data.get("restriction")),
    )


def parse_moderation_event(data: dict[str, Any], channel: str) -> ModerationEvent:
    return ModerationEvent(
        type=data.get("type", "messageDeleted"),
        msg_id=data.get("msgId", ""),
        channel=channel,
    )
