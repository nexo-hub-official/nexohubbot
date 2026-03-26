from discord.ext import commands


class CustomEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomEvents(bot))
