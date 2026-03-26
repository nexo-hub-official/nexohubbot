"""Discord bot entrypoint with modular components.

Setup:
1. Install dependency: `pip install discord.py`
2. Set your bot token: `export DISCORD_BOT_TOKEN=your_token_here`
3. Run: `python bot.py`
"""

from __future__ import annotations

import asyncio
import os

import discord
from discord.ext import commands

COMPONENT_EXTENSIONS = [
    "components.custom_commands",
    "components.custom_events",
    "components.timed_events",
    "components.data_storage",
    "components.webhooks",
    "components.transcripts",
    "components.ifttt",
    "components.message_builder",
    "components.moderation",
    "components.polls_filter",
]


class NexoBot(commands.Bot):
    async def setup_hook(self) -> None:
        for extension in COMPONENT_EXTENSIONS:
            try:
                await self.load_extension(extension)
                print(f"Loaded component: {extension}")
            except Exception as exc:  # pragma: no cover - runtime visibility
                print(f"Failed to load {extension}: {exc}")


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    return NexoBot(command_prefix="!", intents=intents)


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN. Set it before starting the bot.")

    bot = create_bot()
    asyncio.run(bot.start(token))


if __name__ == "__main__":
    main()
