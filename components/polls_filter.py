from discord.ext import commands


class PollsFilter(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="poll")
    async def poll(self, ctx: commands.Context, *, question: str) -> None:
        message = await ctx.send(f"📊 {question}\nReact with 👍 or 👎")
        await message.add_reaction("👍")
        await message.add_reaction("👎")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollsFilter(bot))
