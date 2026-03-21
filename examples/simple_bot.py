"""A simple bot that responds to !ping and !echo commands."""

import os

from hctvwrapper import Bot

bot = Bot(command_prefix="!")


@bot.event
async def on_ready(session):
    print(f"✅ Logged in as {session.viewer}")
    print(f"📺 Connected to: {', '.join(bot.connected_channels)}")
    print(f"🔧 Can moderate: {session.permissions.can_moderate}")


@bot.event
async def on_message(message):
    print(f"[{message.channel}] {message.author.username}: {message.content}")


@bot.command()
async def ping(ctx):
    await ctx.reply("pong! 🏓")


@bot.command(name="echo", aliases=["say"])
async def echo_cmd(ctx, *, text):
    await ctx.send(text)


@bot.command()
async def whoami(ctx):
    author = ctx.author
    role = author.channel_role or "viewer"
    await ctx.reply(f"you are {author.username} ({role})")


token = os.environ.get("BOT_TOKEN")
if not token:
    raise SystemExit("Set the BOT_TOKEN environment variable")

bot.run(token, channel="bot-playground")
