from discord.ext import commands


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        await ctx.send("Pong! 🏓")

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context) -> None:
        await ctx.send(f"Hello, {ctx.author.mention}! 👋")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomCommands(bot))
