"""A bot that uses Hack Club's AI proxy to answer questions."""

import os

import aiohttp

from hctvwrapper import Bot

bot = Bot(command_prefix="/")

AI_URL = "https://ai.hackclub.com/proxy/v1/chat/completions"
AI_TOKEN = os.environ.get("AI_TOKEN", "")


@bot.event
async def on_ready(session):
    print(f"✅ AI bot connected as {session.viewer}")


@bot.command(name="ai")
async def ai_cmd(ctx, *, prompt):
    if not prompt:
        await ctx.reply("usage: /ai <your question>")
        return

    async with aiohttp.ClientSession() as http:
        resp = await http.post(
            AI_URL,
            headers={
                "Authorization": f"Bearer {AI_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-3-flash-preview",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant. Reply concisely "
                            "and like if you were on a chat platform. Use lowercase."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        data = await resp.json()

    answer = data.get("choices", [{}])[0].get("message", {}).get("content")
    if answer:
        await ctx.reply(answer)
    else:
        await ctx.reply("sorry, couldn't get a response")


token = os.environ.get("BOT_TOKEN")
if not token:
    raise SystemExit("Set BOT_TOKEN and AI_TOKEN environment variables")

bot.run(token, channel="bot-playground")
