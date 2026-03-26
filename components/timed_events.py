from discord.ext import commands, tasks


class TimedEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.hourly_heartbeat.start()

    def cog_unload(self) -> None:
        self.hourly_heartbeat.cancel()

    @tasks.loop(hours=1)
    async def hourly_heartbeat(self) -> None:
        print("Timed event: heartbeat")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TimedEvents(bot))
