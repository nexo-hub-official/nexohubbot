"""Discord bot entrypoint with modular components.

Setup:
1. Install dependency: `pip install discord.py`
2. Set your bot token: `export DISCORD_BOT_TOKEN=your_token_here`
3. Run: `python bot.py`

Web app (Flask):
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python web_app.py`
"""

from __future__ import annotations

import asyncio
import os

import discord
from discord import app_commands
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

ROLE_IDS = {
    "owner": 1475147779524268032,
    "coowner": 1484442520967708773,
    "bot_manager": 1486606070402125965,
    "server_manager": 1483717313428717639,
    "head_administrator": 1483717311813914766,
    "administrator": 1483717310257561640,
    "trial_administrator": 1486480724876984542,
    "head_moderator": 1483717307200180265,
    "moderator": 1483717305312743455,
    "trial_moderator": 1483717303731490887,
    "staff_team": 1486481878172041327,
}

PRIVILEGED_ROLE_IDS = {
    ROLE_IDS["owner"],
    ROLE_IDS["coowner"],
    ROLE_IDS["bot_manager"],
    ROLE_IDS["server_manager"],
    ROLE_IDS["head_administrator"],
    ROLE_IDS["administrator"],
    ROLE_IDS["trial_administrator"],
    ROLE_IDS["head_moderator"],
    ROLE_IDS["moderator"],
    ROLE_IDS["trial_moderator"],
}

MANAGEMENT_ROLE_IDS = {
    ROLE_IDS["owner"],
    ROLE_IDS["coowner"],
    ROLE_IDS["bot_manager"],
    ROLE_IDS["server_manager"],
    ROLE_IDS["head_administrator"],
    ROLE_IDS["administrator"],
}


class NexoBot(commands.Bot):
    async def setup_hook(self) -> None:
        for extension in COMPONENT_EXTENSIONS:
            try:
                await self.load_extension(extension)
                print(f"Loaded component: {extension}")
            except Exception as exc:  # pragma: no cover - runtime visibility
                print(f"Failed to load {extension}: {exc}")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")

    async def ensure_staff_team_role(self, member: discord.Member) -> bool:
        if member.guild is None:
            return False

        privileged_role_ids = {role.id for role in member.roles if role.id in PRIVILEGED_ROLE_IDS}
        if not privileged_role_ids:
            return False

        if any(role.id == ROLE_IDS["staff_team"] for role in member.roles):
            return False

        staff_team_role = member.guild.get_role(ROLE_IDS["staff_team"])
        if staff_team_role is None:
            return False

        await member.add_roles(staff_team_role, reason="Auto-added for staff permissions")
        return True

    async def on_member_join(self, member: discord.Member) -> None:
        await self.ensure_staff_team_role(member)

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        before_roles = {role.id for role in before.roles}
        after_roles = {role.id for role in after.roles}
        if before_roles == after_roles:
            return

        await self.ensure_staff_team_role(after)


def has_any_role(member: discord.Member, allowed_role_ids: set[int]) -> bool:
    member_role_ids = {role.id for role in member.roles}
    return bool(member_role_ids.intersection(allowed_role_ids))


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = NexoBot(command_prefix=commands.when_mentioned, intents=intents)

    @bot.tree.command(name="ping", description="Check if the bot is online.")
    async def ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong! 🏓", ephemeral=True)

    @bot.tree.command(
        name="syncstaffrole",
        description="Add the staff team role to members who have staff permissions roles.",
    )
    async def sync_staff_role(interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        if not has_any_role(interaction.user, MANAGEMENT_ROLE_IDS):
            await interaction.response.send_message(
                "You do not have permission to run this command.",
                ephemeral=True,
            )
            return

        staff_team_role = interaction.guild.get_role(ROLE_IDS["staff_team"])
        if staff_team_role is None:
            await interaction.response.send_message(
                "Staff Team role is missing. Verify the role ID in bot.py.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        changed = 0
        for member in interaction.guild.members:
            if has_any_role(member, PRIVILEGED_ROLE_IDS) and staff_team_role not in member.roles:
                await member.add_roles(staff_team_role, reason="Manual /syncstaffrole run")
                changed += 1

        await interaction.followup.send(
            f"Done. Added {staff_team_role.mention} to {changed} member(s).",
            ephemeral=True,
        )

    return bot


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN. Set it before starting the bot.")

    bot = create_bot()
    asyncio.run(bot.start(token))


if __name__ == "__main__":
    main()
