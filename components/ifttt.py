from discord.ext import commands


class IFTTT(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ifttt")
    async def ifttt_status(self, ctx: commands.Context) -> None:
        await ctx.send("IFTTT component scaffold is loaded.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(IFTTT(bot))
