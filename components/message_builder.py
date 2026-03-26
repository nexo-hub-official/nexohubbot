import discord
from discord.ext import commands


class MessageBuilder(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="announce")
    async def announce(self, ctx: commands.Context, *, message: str) -> None:
        embed = discord.Embed(title="Announcement", description=message, color=0x2ECC71)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageBuilder(bot))
