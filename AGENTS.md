# AGENTS.md — hctvwrapper

## What this project is

A Pycord-style Python wrapper for [hackclub.tv](https://hackclub.tv) WebSocket chat API. Users build bots with `@bot.event` and `@bot.command()` decorators.

## Architecture

- `hctvwrapper/bot.py` — Main `Bot` class: decorators, command dispatch, event firing, lifecycle
- `hctvwrapper/connection.py` — WebSocket management: `ChannelConnection` (single socket), `ConnectionManager` (multi-channel, reconnect), and all JSON→model parsers
- `hctvwrapper/context.py` — `Context` object passed to command handlers (`ctx.reply()`, `ctx.send()`, `ctx.delete()`)
- `hctvwrapper/models.py` — Dataclass models: `Message`, `Author`, `Session`, `ChatAccess`, etc.
- `hctvwrapper/__init__.py` — Public API re-exports and `__version__`

## Conventions

- **Async-first**: All bot/connection methods are async. `bot.run()` is the only sync wrapper (calls `asyncio.run`).
- **Dataclasses only**: All models are `@dataclass`. No Pydantic, no attrs.
- **Single dependency**: Only `websockets`. Do not add other dependencies.
- **Python 3.10+**: Use `X | Y` union syntax, not `Union[X, Y]`. Use `from __future__ import annotations`.
- **Typed**: The package ships `py.typed`. All public methods must have type annotations.
- **Logging**: Use `logging.getLogger("hctvwrapper")`, never `print()`.
- **No comments unless complex**: Code should be self-explanatory. Only add comments for non-obvious logic.

## Key rules

- **Backward compatibility matters**: All changes must keep existing bots working. New params must have defaults. Never rename or remove public API.
- **Version in two places**: `pyproject.toml` and `hctvwrapper/__init__.py` must match.
- **WebSocket URL**: `wss://hackclub.tv/api/stream/chat/ws/{channel}` — confirmed from the hctv source code.
- **Ping every 5 seconds**: Cloudflare kills idle connections. The `ChannelConnection._ping_loop` handles this.
- **Auto-reconnect**: Exponential backoff (1s→60s). Configurable via `auto_reconnect` and `reconnect_max_attempts` on `Bot`.
- **`on_ready` fires once**: Even with multiple channels, `on_ready` only fires on the first `session` message.
- **Error isolation**: Exceptions in event/command handlers are caught, logged, and routed to `on_error` — never crash the bot.

## Testing changes

```bash
# Quick import check
.venv/bin/python -c "from hctvwrapper import Bot; print('OK')"

# Verify backward compat with all examples
.venv/bin/python -c "import ast; [ast.parse(open(f).read()) for f in ['examples/simple_bot.py','examples/ai_bot.py','examples/multi_channel.py']]; print('OK')"
```

## API reference

The hackclub.tv WebSocket API is documented at https://docs.hackclub.tv/api/chat and in the server source at https://github.com/SrIzan10/hctv (apps/chat/src/index.ts).
