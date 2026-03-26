from discord.ext import commands


class Transcripts(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="transcript")
    async def transcript(self, ctx: commands.Context) -> None:
        await ctx.send("Transcript feature scaffold is loaded.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Transcripts(bot))
