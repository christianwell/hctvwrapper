"""A bot that listens to multiple channels at once."""

import os

from hctvwrapper import Bot

bot = Bot(command_prefix="!")


@bot.event
async def on_ready(session):
    print(f"✅ Connected to: {', '.join(bot.connected_channels)}")


@bot.event
async def on_message(message):
    print(f"[{message.channel}] {message.author.username}: {message.content}")


@bot.event
async def on_system_message(message):
    print(f"[{message.channel}] SYSTEM: {message.content}")


@bot.command()
async def ping(ctx):
    await ctx.reply(f"pong from {ctx.channel}! 🏓")


@bot.command()
async def channels(ctx):
    ch_list = ", ".join(bot.connected_channels)
    await ctx.reply(f"i'm in: {ch_list}")


token = os.environ.get("BOT_TOKEN")
if not token:
    raise SystemExit("Set the BOT_TOKEN environment variable")

bot.run(token, channels=["channel1", "channel2", "bot-playground"])
