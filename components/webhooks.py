from discord.ext import commands


class Webhooks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="webhookstatus")
    async def webhook_status(self, ctx: commands.Context) -> None:
        await ctx.send("Webhook component is enabled.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Webhooks(bot))
