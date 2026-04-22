# hctvwrapper v0.1.0

A Pycord-style Python wrapper for [hackclub.tv](https://hackclub.tv)

---

## Table of Contents

- [Install](#install)
- [Getting a Bot Token](#getting-a-bot-token)
- [Quick Start](#quick-start)
- [Bot](#bot)
  - [Properties](#properties)
  - [Methods](#methods)
- [Events](#events)
  - [on_ready](#on_readysession)
  - [on_message](#on_messagemessage)
  - [on_history](#on_historymessages)
  - [on_system_message](#on_system_messagemessage)
  - [on_message_deleted](#on_message_deletedevent)
  - [on_chat_access](#on_chat_accessaccess-channel)
  - [on_moderation_error](#on_moderation_errorerror-channel)
  - [on_emoji_response](#on_emoji_responseemojis)
  - [on_emoji_search](#on_emoji_searchresults)
- [Commands](#commands)
- [Context](#context)
- [Sending Messages](#sending-messages)
- [Multi-Channel](#multi-channel)
- [Moderation](#moderation)
- [Emojis](#emojis)
- [Async Usage](#async-usage)
- [Error Handling](#error-handling)
- [Models Reference](#models-reference)
- [Examples](#examples)

---

## Install

```bash
pip install hctvwrapper
```

Only dependency: `websockets` — requires Python 3.10+

## Getting a Bot Token

1. Go to [hackclub.tv](https://hackclub.tv)
2. Create a bot account and get your API key (starts with `hctvb_`)
3. Set it as an environment variable: `export BOT_TOKEN=hctvb_xxx`

## Quick Start

```python
from hctvwrapper import Bot

bot = Bot(command_prefix="!")

@bot.event
async def on_ready(session):
    print(f"Logged in as {session.viewer}")

@bot.command()
async def ping(ctx):
    await ctx.reply("pong! 🏓")

bot.run("hctvb_your_token", channel="bot-playground")
```

## Bot

The `Bot` class is the main entry point. It handles connections, events, and commands.

```python
bot = Bot(command_prefix="!")  # prefix for commands, default "!"
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `bot.session` | `Session \| None` | Session info after connecting |
| `bot.connected_channels` | `list[str]` | List of connected channel names |
| `bot.is_connected` | `bool` | Whether the bot is connected to any channel |
| `bot.command_prefix` | `str` | The command prefix |

### Methods

| Method | Description |
|--------|-------------|
| `bot.run(token, channel=, channels=)` | Blocking entry point — starts the bot |
| `await bot.start(token, channel=, channels=)` | Async entry point |
| `await bot.send(content, channel=)` | Send a message |
| `bot.is_connected_to(channel)` | Check if connected to a specific channel |

## Events

Register event handlers with `@bot.event`. The function name determines which event it handles.

### on_ready(session)

Fired once when the bot connects and receives session info.

```python
@bot.event
async def on_ready(session):
    print(f"Logged in as {session.viewer.username}")
    print(f"Can moderate: {session.permissions.can_moderate}")
    print(f"Max msg length: {session.moderation.max_message_length}")
```

### on_message(message)

Fired on every incoming chat message.

```python
@bot.event
async def on_message(message):
    print(f"[{message.channel}] {message.author.username}: {message.content}")
```

### on_history(messages)

Fired once on connect with up to 100 recent messages.

```python
@bot.event
async def on_history(messages):
    print(f"Got {len(messages)} historical messages")
```

### on_system_message(message)

Fired on system notifications (bans, unbans, etc.).

```python
@bot.event
async def on_system_message(message):
    print(f"System: {message.content}")
```

### on_message_deleted(event)

Fired when a message is deleted by a moderator.

```python
@bot.event
async def on_message_deleted(event):
    print(f"Deleted {event.msg_id} in {event.channel}")
```

### on_chat_access(access, channel)

Fired when chat permissions change (timeouts, bans).

```python
@bot.event
async def on_chat_access(access, channel):
    print(f"Can send in {channel}: {access.can_send}")
    if access.restriction:
        print(f"Restriction: {access.restriction.type}")
```

### on_moderation_error(error, channel)

Fired when a moderation action or message is rejected.

```python
@bot.event
async def on_moderation_error(error, channel):
    print(f"Error: {error.code} — {error.message}")
```

> **ℹ Error codes:** FORBIDDEN, RATE_LIMIT, SLOW_MODE, TIMED_OUT, BANNED, MESSAGE_TOO_LONG, BLOCKED_TERM, INVALID_TARGET, INVALID_REQUEST, NOT_FOUND

### on_emoji_response(emojis)

Fired when emoji URL lookups complete (in response to `bot.lookup_emojis()`).

```python
@bot.event
async def on_emoji_response(emojis):
    # emojis is a dict mapping emoji names to URLs
    # e.g. {"yay": "https://...", "aga": "https://..."}
    for name, url in emojis.items():
        print(f":{name}: → {url}")
```

### on_emoji_search(results)

Fired when an emoji search completes (in response to `bot.search_emojis()`).

```python
@bot.event
async def on_emoji_search(results):
    # results is a list of matching emoji names
    # e.g. ["yay", "yay-bounce", "yay-spin", ...]
    print(f"Found {len(results)} emojis: {results}")
```

## Commands

Register prefix commands with `@bot.command()`. The bot automatically parses messages that start with the prefix.

### Simple command

```python
@bot.command()
async def ping(ctx):
    await ctx.reply("pong!")
```

### Named command with aliases

```python
@bot.command(name="say", aliases=["echo", "repeat"])
async def say_cmd(ctx, *, text):
    await ctx.send(text)
```

### Positional arguments

```python
@bot.command()
async def greet(ctx, name, greeting="hello"):
    await ctx.reply(f"{greeting}, {name}!")
```

### Keyword-only (rest of message)

Use `*, text` to capture everything after the command as a single string:

```python
@bot.command()
async def echo(ctx, *, text):
    await ctx.reply(text)
# !echo hello world foo  →  text = "hello world foo"
```

> **ℹ Note:** The bot automatically ignores its own messages to prevent loops.

## Context

The `ctx` object passed to every command handler:

| Property / Method | Description |
|-------------------|-------------|
| `ctx.message` | The full `Message` object |
| `ctx.author` | Shortcut to `message.author` (`Author`) |
| `ctx.channel` | Channel name (`str`) |
| `ctx.content` | Raw message content |
| `ctx.bot` | Reference to the `Bot` |
| `await ctx.reply(text)` | Send `@username text` |
| `await ctx.send(text)` | Send without mention |
| `await ctx.delete()` | Delete triggering message (needs mod perms) |

## Sending Messages

```python
# in a command
await ctx.reply("mentioned reply")
await ctx.send("plain message")

# anywhere
await bot.send("hello!", channel="bot-playground")
```

## Multi-Channel

```python
bot.run("hctvb_xxx", channels=["channel1", "channel2", "bot-playground"])
```

Events and commands work across all channels. Use `message.channel` or `ctx.channel` to know the source.

```python
@bot.command()
async def where(ctx):
    await ctx.reply(f"you're in {ctx.channel}")
```

## Moderation

Bots with moderation permissions can manage users:

```python
# Timeout (10–86400 seconds, default 300)
await bot.timeout_user("channel", user_id="user123", duration=300, reason="spam")

# Ban
await bot.ban_user("channel", user_id="user123", reason="violations")

# Remove timeout
await bot.lift_timeout("channel", user_id="user123")

# Unban
await bot.unban_user("channel", user_id="user123")

# Delete a message
await bot.delete_message("channel", msg_id="msg-uuid")
```

## Emojis

Look up or search Slack-style emojis. Results come back via events.

```python
# Look up emoji URLs
await bot.lookup_emojis(["yay", "aga"])

# Search emojis
await bot.search_emojis("yay")

# Handle results
@bot.event
async def on_emoji_response(emojis):
    # emojis = {"yay": "https://...", "aga": "https://..."}
    print(emojis)

@bot.event
async def on_emoji_search(results):
    # results = ["yay", "yay-bounce", "yay-spin", ...]
    print(results)
```

## Async Usage

If you manage your own event loop, use `await bot.start()` instead of `bot.run()`:

```python
import asyncio

async def main():
    bot = Bot(command_prefix="!")

    @bot.event
    async def on_ready(session):
        print("Connected!")

    await bot.start("hctvb_xxx", channel="bot-playground")

asyncio.run(main())
```

## Error Handling

Errors from the hackclub.tv server (rejected messages, failed moderation actions) are delivered via the `on_moderation_error` event:

```python
@bot.event
async def on_moderation_error(error, channel):
    print(f"[{channel}] {error.code}: {error.message}")
    if error.restriction:
        print(f"  Restriction: {error.restriction.type}, expires: {error.restriction.expires_at}")
```

The `error.code` will be one of: `FORBIDDEN`, `RATE_LIMIT`, `SLOW_MODE`, `TIMED_OUT`, `BANNED`, `MESSAGE_TOO_LONG`, `BLOCKED_TERM`, `INVALID_TARGET`, `INVALID_REQUEST`, `NOT_FOUND`.

If the bot attempts to send a message while not connected to any channel, a `RuntimeError` is raised:

```python
try:
    await bot.send("hello!")
except RuntimeError as e:
    print(f"Not connected: {e}")
```

## Models Reference

### Message

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Message text |
| `author` | `Author` | Who sent it |
| `channel` | `str` | Channel name |
| `msg_id` | `str \| None` | Server message UUID |
| `timestamp` | `float` | Unix timestamp |
| `type` | `str` | `"message"` or `"systemMsg"` |
| `is_bot` | `bool` | Whether the author is a bot |

### Author

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | User ID |
| `username` | `str` | Username |
| `display_name` | `str \| None` | Display name |
| `pfp_url` | `str \| None` | Profile picture URL |
| `is_bot` | `bool` | Is a bot account |
| `is_platform_admin` | `bool` | Is a platform admin |
| `channel_role` | `str \| None` | `owner`, `manager`, `chatModerator`, `botModerator`, or `None` |

### Session

| Field | Type | Description |
|-------|------|-------------|
| `viewer` | `Author \| None` | The bot's own user info |
| `permissions` | `Permissions` | `.can_moderate` — bool |
| `moderation` | `ModerationSettings` | `.has_blocked_terms`, `.slow_mode_seconds`, `.max_message_length` |

### ChatAccess

| Field | Type | Description |
|-------|------|-------------|
| `can_send` | `bool` | Whether the bot can send messages |
| `restriction` | `Restriction \| None` | Active restriction details |

### Restriction

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"timeout"` or `"ban"` |
| `reason` | `str \| None` | Reason for the restriction |
| `expires_at` | `str \| None` | ISO 8601 expiry (timeouts) or None (bans) |

### ModerationError

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Error code (see list above) |
| `message` | `str` | Human-readable error message |
| `restriction` | `Restriction \| None` | Present for TIMED_OUT / BANNED codes |

### ModerationEvent

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"messageDeleted"` |
| `msg_id` | `str` | UUID of deleted message |
| `channel` | `str` | Channel name |

### SystemMessage

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"connected"`, `"disconnected"`, `"error"`, `"system"` |
| `channel` | `str` | Channel name |
| `content` | `str` | System message text |
| `timestamp` | `float` | Unix timestamp |

## Examples

### Echo Bot

```python
from hctvwrapper import Bot
import os

bot = Bot(command_prefix="!")

@bot.event
async def on_ready(session):
    print(f"✅ Logged in as {session.viewer}")

@bot.command()
async def ping(ctx):
    await ctx.reply("pong! 🏓")

@bot.command(name="echo", aliases=["say"])
async def echo_cmd(ctx, *, text):
    await ctx.send(text)

bot.run(os.environ["BOT_TOKEN"], channel="bot-playground")
```

### AI Bot

```python
from hctvwrapper import Bot
import aiohttp, os

bot = Bot(command_prefix="/")

@bot.command(name="ai")
async def ai_cmd(ctx, *, prompt):
    async with aiohttp.ClientSession() as http:
        resp = await http.post(
            "https://ai.hackclub.com/proxy/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['AI_TOKEN']}"},
            json={
                "model": "google/gemini-3-flash-preview",
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        data = await resp.json()
    answer = data["choices"][0]["message"]["content"]
    await ctx.reply(answer)

bot.run(os.environ["BOT_TOKEN"], channel="bot-playground")
```

### Moderation Bot

```python
from hctvwrapper import Bot
import os

bot = Bot(command_prefix="!")

@bot.command()
async def timeout(ctx, user_id, seconds="300"):
    await bot.timeout_user(ctx.channel, user_id, duration=int(seconds))
    await ctx.send(f"⏰ Timed out for {seconds}s")

@bot.event
async def on_moderation_error(error, channel):
    print(f"⚠️ {error.code}: {error.message}")

bot.run(os.environ["BOT_TOKEN"], channel="my-channel")
```

---

hctvwrapper v0.1.0 · [hackclub.tv](https://hackclub.tv) · [API Docs](https://docs.hackclub.tv/api/chat)
