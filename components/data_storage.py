from __future__ import annotations

import json
from pathlib import Path

from discord.ext import commands

DATA_FILE = Path("bot_data.json")


class DataStorage(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="setnote")
    async def set_note(self, ctx: commands.Context, *, note: str) -> None:
        payload = {"user_id": str(ctx.author.id), "note": note}
        DATA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        await ctx.send("Saved a note in bot_data.json")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DataStorage(bot))
