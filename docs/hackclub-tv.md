# hctvwrapper

A Python wrapper for [hackclub.tv](https://hackclub.tv) bots. If you've used Discord.py or Pycord, this will feel familiar.

---

## Table of Contents

- [Install](#install)
- [Get a Bot Token](#get-a-bot-token)
- [Your First Bot](#your-first-bot)
- [Events](#events)
- [Commands](#commands)
- [Context — the `ctx` object](#context--the-ctx-object)
- [Sending Messages](#sending-messages)
- [Checking User Roles](#checking-user-roles)
- [Multiple Channels](#multiple-channels)
- [Moderation](#moderation)
- [Emojis](#emojis)
- [Auto-Reconnect](#auto-reconnect)
- [Error Handling](#error-handling)
- [Async Usage](#async-usage)
- [All Models](#all-models)
- [Examples](#examples)

---

## Install

```bash
pip install hctvwrapper
```

That's it. The only dependency is `websockets`. You need Python 3.10 or newer.

---

## Get a Bot Token

1. Go to [hackclub.tv](https://hackclub.tv)
2. Create a bot account
3. Copy the API key — it starts with `hctvb_`
4. Save it somewhere safe (never share it!)

Set it as an environment variable so your code doesn't contain the token:

```bash
export BOT_TOKEN=hctvb_your_key_here
```

---

## Your First Bot

```python
import os
from hctvwrapper import Bot

# 1. Create a bot — "!" means commands start with !
bot = Bot(command_prefix="!")

# 2. This runs when the bot connects
@bot.event
async def on_ready(session):
    print(f"Bot is online! Logged in as {session.viewer}")

# 3. This runs when someone types !ping
@bot.command()
async def ping(ctx):
    await ctx.reply("pong! 🏓")

# 4. Start the bot
bot.run(os.environ["BOT_TOKEN"], channel="bot-playground")
```

Run it:

```bash
python my_bot.py
```

That's a working bot! Type `!ping` in chat and it replies `@you pong! 🏓`.

---

## Events

Events let your bot react to things that happen in chat. Use `@bot.event` and name the function after the event you want.

### on_ready — bot connected

Runs **once** when the bot first connects (even if you join multiple channels).

```python
@bot.event
async def on_ready(session):
    print(f"Logged in as {session.viewer.username}")
    print(f"Can moderate: {session.permissions.can_moderate}")
```

### on_message — someone sent a message

Runs every time anyone sends a message.

```python
@bot.event
async def on_message(message):
    print(f"{message.author.username}: {message.content}")

    # You can check things about the message:
    # message.channel    — which channel it's in
    # message.author     — who sent it (Author object)
    # message.msg_id     — unique ID of the message
    # message.is_bot     — True if sent by a bot
```

### on_history — old messages on connect

When your bot connects, it gets up to 100 recent messages.

```python
@bot.event
async def on_history(messages):
    print(f"Got {len(messages)} old messages")
```

### on_system_message — bans, unbans, etc.

```python
@bot.event
async def on_system_message(message):
    print(f"System: {message.content}")
    # Example: "someone was banned."
```

### on_message_deleted — a mod deleted a message

```python
@bot.event
async def on_message_deleted(event):
    print(f"Message {event.msg_id} was deleted in {event.channel}")
```

### on_chat_access — your bot got timed out or banned

```python
@bot.event
async def on_chat_access(access, channel):
    if access.can_send:
        print("We can chat!")
    else:
        print(f"We're restricted: {access.restriction.type}")
        # access.restriction.type is "timeout" or "ban"
        # access.restriction.reason has the reason
```

### on_disconnect — lost connection

```python
@bot.event
async def on_disconnect(channel):
    print(f"Lost connection to {channel}")
```

### on_reconnect — reconnected after a drop

```python
@bot.event
async def on_reconnect(channel):
    print(f"Back online in {channel}!")
```

### on_error — something crashed

Runs when an event handler or command throws an error. Without this, errors are just logged.

```python
@bot.event
async def on_error(source, error):
    # source is like "on_message" or "command:ping"
    print(f"Error in {source}: {error}")
```

---

## Commands

Commands are messages that start with your prefix (like `!`). The bot parses them automatically.

### Simple command

```python
@bot.command()
async def ping(ctx):
    await ctx.reply("pong!")
```

`!ping` → `@user pong!`

### Command with a different name

```python
@bot.command(name="say", aliases=["echo", "repeat"])
async def say_cmd(ctx, *, text):
    await ctx.send(text)
```

`!say hello world` → `hello world`
`!echo hello world` → `hello world` (alias works too)

### Command with arguments

Arguments are split by spaces:

```python
@bot.command()
async def greet(ctx, name, greeting="hello"):
    await ctx.reply(f"{greeting}, {name}!")
```

`!greet Alice` → `@user hello, Alice!`
`!greet Alice hey` → `@user hey, Alice!`

If someone forgets a required argument, the bot tells them:

`!greet` → `@user missing arguments: name`

### Grab the whole message

Use `*, text` to get everything after the command as one string:

```python
@bot.command()
async def echo(ctx, *, text):
    await ctx.reply(text)
```

`!echo hello world foo` → `@user hello world foo`

---

## Context — the `ctx` object

Every command gets a `ctx` (context) object. It has everything you need:

```python
@bot.command()
async def info(ctx):
    ctx.message     # the full Message object
    ctx.author      # who sent the command (Author)
    ctx.channel     # channel name (string)
    ctx.bot         # the Bot itself

    await ctx.reply("hi")     # sends "@username hi"
    await ctx.send("hi")      # sends "hi" (no mention)
    await ctx.delete()        # deletes the command message (needs mod perms)
```

---

## Sending Messages

```python
# Inside a command — easiest way
await ctx.reply("hello!")       # @user hello!
await ctx.send("hello!")        # hello! (no mention)

# From anywhere (if you have the bot)
await bot.send("hello!", channel="bot-playground")
```

---

## Checking User Roles

Every user has a `channel_role`. You can check it easily:

```python
@bot.command()
async def whoami(ctx):
    author = ctx.author

    # Quick checks — returns True/False
    author.is_owner           # channel owner
    author.is_manager         # channel manager
    author.is_moderator       # chat or bot moderator
    author.is_staff           # any of the above (owner/manager/mod)
    author.is_bot             # is a bot account
    author.is_platform_admin  # hackclub.tv admin

    # Check specific roles
    author.has_role("owner", "manager")  # True if owner OR manager

    # Get the raw role string
    author.channel_role  # "owner" / "manager" / "chatModerator" / "botModerator" / None
```

### Example: owner-only command

```python
@bot.command()
async def secret(ctx):
    if not ctx.author.is_owner:
        await ctx.reply("only the channel owner can use this!")
        return
    await ctx.reply("you're the boss 👑")
```

### Example: staff-only moderation

```python
@bot.command()
async def kick(ctx, user_id):
    if not ctx.author.is_staff:
        await ctx.reply("you don't have permission!")
        return
    await bot.timeout_user(ctx.channel, user_id=user_id, duration=60)
    await ctx.send(f"⏰ timed out for 60s")
```

### Role hierarchy

From lowest to highest:

| Role | Value |
|------|-------|
| `None` (regular viewer) | — |
| `chatModerator` | can moderate chat |
| `botModerator` | can moderate bots |
| `manager` | can manage the channel |
| `owner` | owns the channel |
| platform admin | hackclub.tv staff |

---

## Multiple Channels

Connect to several channels at once:

```python
bot.run("hctvb_xxx", channels=["channel1", "channel2", "bot-playground"])
```

Use `ctx.channel` or `message.channel` to know where a message came from:

```python
@bot.command()
async def where(ctx):
    await ctx.reply(f"you're in {ctx.channel}")
```

---

## Moderation

Your bot needs mod permissions for these. Check with `session.permissions.can_moderate`.

```python
# Timeout someone for 5 minutes (300 seconds)
await bot.timeout_user("channel", user_id="user123", duration=300, reason="spam")

# Ban someone permanently
await bot.ban_user("channel", user_id="user123", reason="goodbye")

# Undo a timeout
await bot.lift_timeout("channel", user_id="user123")

# Undo a ban
await bot.unban_user("channel", user_id="user123")

# Delete a message
await bot.delete_message("channel", msg_id="message-uuid")
```

Timeout duration must be between 10 and 86400 seconds (10s to 24h). Default is 300 (5 min).

---

## Emojis

Look up or search for Slack-style emojis. Results come back through events.

```python
# Look up emoji URLs by name
await bot.lookup_emojis(["yay", "aga"])

# Search for emojis matching a term
await bot.search_emojis("yay")

# Get the results
@bot.event
async def on_emoji_response(emojis):
    # emojis = {"yay": "https://...", "aga": "https://..."}
    for name, url in emojis.items():
        print(f":{name}: → {url}")

@bot.event
async def on_emoji_search(results):
    # results = ["yay", "yay-bounce", "yay-spin", ...]
    print(f"Found: {results}")
```

---

## Auto-Reconnect

By default, if your bot loses connection, it automatically reconnects with exponential backoff (waits 1s, 2s, 4s, 8s... up to 60s between attempts).

```python
# Default: auto-reconnect forever
bot = Bot(command_prefix="!")

# Limit to 10 reconnect attempts
bot = Bot(command_prefix="!", reconnect_max_attempts=10)

# Disable auto-reconnect entirely
bot = Bot(command_prefix="!", auto_reconnect=False)
```

Use `on_disconnect` and `on_reconnect` events to know when it happens:

```python
@bot.event
async def on_disconnect(channel):
    print(f"Lost connection to {channel}, reconnecting...")

@bot.event
async def on_reconnect(channel):
    print(f"Back online in {channel}!")
```

### Shutting down cleanly

```python
# Inside an async function
await bot.close()  # disconnects everything, stops reconnecting
```

---

## Error Handling

### Server errors (rejected messages, no permissions)

These come through the `on_moderation_error` event:

```python
@bot.event
async def on_moderation_error(error, channel):
    print(f"[{channel}] {error.code}: {error.message}")
```

Possible error codes:

| Code | What happened |
|------|---------------|
| `FORBIDDEN` | You don't have permission |
| `RATE_LIMIT` | Sending messages too fast |
| `SLOW_MODE` | Slow mode is on, wait a bit |
| `TIMED_OUT` | Your bot is timed out |
| `BANNED` | Your bot is banned |
| `MESSAGE_TOO_LONG` | Message is too long |
| `BLOCKED_TERM` | Message contains a blocked word |
| `INVALID_TARGET` | Tried to mod someone who doesn't exist |
| `INVALID_REQUEST` | Bad moderation command |
| `NOT_FOUND` | Tried to delete a message that doesn't exist |

### Code errors (bugs in your handlers)

If your command or event handler crashes, the bot catches it and logs it instead of dying. You can also handle it yourself:

```python
@bot.event
async def on_error(source, error):
    print(f"Bug in {source}: {error}")
```

### Not connected

If you try to send a message when not connected, you get a `RuntimeError`:

```python
try:
    await bot.send("hello!")
except RuntimeError as e:
    print(f"Not connected: {e}")
```

---

## Async Usage

If you manage your own event loop, use `await bot.start()` instead of `bot.run()`:

```python
import asyncio
from hctvwrapper import Bot

async def main():
    bot = Bot(command_prefix="!")

    @bot.event
    async def on_ready(session):
        print("Connected!")

    await bot.start("hctvb_xxx", channel="bot-playground")

asyncio.run(main())
```

---

## All Models

### Author

The person who sent a message.

| Field | Type | What it is |
|-------|------|------------|
| `id` | `str` | Their user ID |
| `username` | `str` | Their username |
| `display_name` | `str or None` | Their display name (if set) |
| `pfp_url` | `str or None` | Profile picture URL |
| `channel_role` | `str or None` | `"owner"`, `"manager"`, `"chatModerator"`, `"botModerator"`, or `None` |
| `is_bot` | `bool` | Is this a bot? |
| `is_platform_admin` | `bool` | Is this a hackclub.tv admin? |
| `is_owner` | `bool` | Is this the channel owner? |
| `is_manager` | `bool` | Is this a channel manager? |
| `is_moderator` | `bool` | Is this a chat or bot moderator? |
| `is_staff` | `bool` | Is this owner, manager, or mod? |

Methods: `has_role("owner", "manager")` — returns True if the user has any of those roles.

### Message

A chat message.

| Field | Type | What it is |
|-------|------|------------|
| `content` | `str` | The message text |
| `author` | `Author` | Who sent it |
| `channel` | `str` | Which channel |
| `msg_id` | `str or None` | Unique message ID |
| `timestamp` | `float` | When it was sent (unix time) |
| `is_bot` | `bool` | Was it sent by a bot? |

### Session

Info about your bot's connection.

| Field | Type | What it is |
|-------|------|------------|
| `viewer` | `Author or None` | Your bot's user info |
| `permissions.can_moderate` | `bool` | Can your bot moderate? |
| `moderation.slow_mode_seconds` | `int` | Slow mode delay (0 = off) |
| `moderation.max_message_length` | `int` | Max message length (default 400) |
| `moderation.has_blocked_terms` | `bool` | Are there blocked words? |

### Other Models

| Model | Fields | Used in |
|-------|--------|---------|
| `ChatAccess` | `can_send`, `restriction` | `on_chat_access` event |
| `Restriction` | `type` (timeout/ban), `reason`, `expires_at` | Inside ChatAccess/ModerationError |
| `ModerationError` | `code`, `message`, `restriction` | `on_moderation_error` event |
| `ModerationEvent` | `type`, `msg_id`, `channel` | `on_message_deleted` event |
| `SystemMessage` | `type`, `channel`, `content`, `timestamp` | `on_system_message` event |

---

## Examples

### Echo Bot

```python
import os
from hctvwrapper import Bot

bot = Bot(command_prefix="!")

@bot.event
async def on_ready(session):
    print(f"✅ Online as {session.viewer}")

@bot.command()
async def ping(ctx):
    await ctx.reply("pong! 🏓")

@bot.command(name="echo", aliases=["say"])
async def echo_cmd(ctx, *, text):
    await ctx.send(text)

bot.run(os.environ["BOT_TOKEN"], channel="bot-playground")
```

### Staff-Only Bot

```python
import os
from hctvwrapper import Bot

bot = Bot(command_prefix="!")

@bot.command()
async def timeout(ctx, user_id, seconds="300"):
    if not ctx.author.is_staff:
        await ctx.reply("no permission!")
        return
    await bot.timeout_user(ctx.channel, user_id, duration=int(seconds))
    await ctx.send(f"⏰ Timed out for {seconds}s")

@bot.event
async def on_moderation_error(error, channel):
    print(f"⚠️ {error.code}: {error.message}")

bot.run(os.environ["BOT_TOKEN"], channel="my-channel")
```

### AI Bot

```python
import os
import aiohttp
from hctvwrapper import Bot

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

---

hctvwrapper · [hackclub.tv](https://hackclub.tv) · [GitHub](https://github.com/christianwell/hctvwrapper)
