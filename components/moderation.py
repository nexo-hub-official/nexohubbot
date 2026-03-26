from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import timedelta
from typing import Deque, DefaultDict

import discord
from discord.ext import commands


class Moderation(commands.Cog):
    """Ghost-style moderation toolkit with practical defaults."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.mod_log_channel_id = 1486610796787269732
        self._case_counter = 0
        self._recent_messages: DefaultDict[int, Deque[float]] = defaultdict(
            lambda: deque(maxlen=8)
        )

    def _next_case_id(self) -> int:
        self._case_counter += 1
        return self._case_counter

    def _mod_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel = guild.get_channel(self.mod_log_channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    def _build_dm_embed(
        self,
        *,
        action: str,
        moderator: discord.abc.User,
        time_text: str,
        case_id: int,
        reason: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            title="Moderation Notice",
            description=(
                "A moderation action has been applied to you.\n\n"
                f"Punishment: {action}\n"
                f"Moderator: {moderator}\n"
                f"Time: {time_text}\n"
                f"Case ID: {case_id}\n"
                f"Reason: {reason}"
            ),
            color=discord.Color.red(),
        )
        return embed

    def _build_log_embed(
        self,
        *,
        action: str,
        target: discord.abc.User,
        moderator: discord.abc.User,
        time_text: str,
        case_id: int,
        reason: str,
    ) -> discord.Embed:
        embed = discord.Embed(title="Moderation Log", color=discord.Color.green())
        embed.add_field(name="Action", value=action, inline=True)
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=True)
        embed.add_field(
            name="Moderator",
            value=f"{moderator} (`{moderator.id}`)",
            inline=True,
        )
        embed.add_field(name="Time", value=time_text, inline=True)
        embed.add_field(name="Case ID", value=str(case_id), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        return embed

    async def _send_punishment_dm(
        self,
        *,
        member: discord.abc.User,
        action: str,
        moderator: discord.abc.User,
        time_text: str,
        case_id: int,
        reason: str,
    ) -> None:
        embed = self._build_dm_embed(
            action=action,
            moderator=moderator,
            time_text=time_text,
            case_id=case_id,
            reason=reason,
        )
        try:
            await member.send(embed=embed)
        except discord.HTTPException:
            pass

    async def _send_mod_log(
        self,
        *,
        guild: discord.Guild,
        target: discord.abc.User,
        action: str,
        moderator: discord.abc.User,
        time_text: str,
        case_id: int,
        reason: str,
    ) -> None:
        channel = self._mod_log_channel(guild)
        if channel is None:
            return

        embed = self._build_log_embed(
            action=action,
            target=target,
            moderator=moderator,
            time_text=time_text,
            case_id=case_id,
            reason=reason,
        )
        await channel.send(embed=embed)

    async def _ensure_manageable(
        self,
        ctx: commands.Context,
        member: discord.Member,
        action: str,
    ) -> bool:
        if member == ctx.author:
            await ctx.send(f"❌ You cannot {action} yourself.")
            return False

        if member == ctx.guild.me:
            await ctx.send(f"❌ I cannot {action} myself.")
            return False

        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send(
                f"❌ You cannot {action} a member with an equal/higher role than you."
            )
            return False

        if ctx.guild.me.top_role <= member.top_role:
            await ctx.send(
                f"❌ I cannot {action} that member due to role hierarchy limitations."
            )
            return False

        return True

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        amount = max(1, min(amount, 100))
        deleted = await ctx.channel.purge(limit=amount + 1)
        confirm = await ctx.send(f"🧹 Cleared {max(0, len(deleted) - 1)} messages.")
        await asyncio.sleep(4)
        await confirm.delete()

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._ensure_manageable(ctx, member, "kick"):
            return

        case_id = self._next_case_id()
        await self._send_punishment_dm(
            member=member,
            action="Kick",
            moderator=ctx.author,
            time_text="Permanent",
            case_id=case_id,
            reason=reason,
        )
        await member.kick(reason=f"{ctx.author} | {reason}")
        await self._send_mod_log(
            guild=ctx.guild,
            target=member,
            action="Kick",
            moderator=ctx.author,
            time_text="Permanent",
            case_id=case_id,
            reason=reason,
        )
        await ctx.send(f"👢 Kicked {member.mention} • Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._ensure_manageable(ctx, member, "ban"):
            return

        case_id = self._next_case_id()
        await self._send_punishment_dm(
            member=member,
            action="Ban",
            moderator=ctx.author,
            time_text="Permanent",
            case_id=case_id,
            reason=reason,
        )
        await member.ban(
            reason=f"{ctx.author} | {reason}",
            delete_message_seconds=604800,
        )
        await self._send_mod_log(
            guild=ctx.guild,
            target=member,
            action="Ban",
            moderator=ctx.author,
            time_text="Permanent",
            case_id=case_id,
            reason=reason,
        )
        await ctx.send(f"🔨 Banned {member.mention} • Reason: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int) -> None:
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"{ctx.author} requested unban")
        await ctx.send(f"✅ Unbanned {user}.")

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        minutes: int = 10,
        *,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._ensure_manageable(ctx, member, "mute"):
            return

        minutes = max(1, min(minutes, 40320))
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        case_id = self._next_case_id()
        await self._send_punishment_dm(
            member=member,
            action="Mute",
            moderator=ctx.author,
            time_text=f"{minutes} minute(s)",
            case_id=case_id,
            reason=reason,
        )
        await member.timeout(until, reason=f"{ctx.author} | {reason}")
        await self._send_mod_log(
            guild=ctx.guild,
            target=member,
            action="Mute",
            moderator=ctx.author,
            time_text=f"{minutes} minute(s)",
            case_id=case_id,
            reason=reason,
        )
        await ctx.send(
            f"🔇 Muted {member.mention} for {minutes} minute(s) • Reason: {reason}"
        )

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._ensure_manageable(ctx, member, "unmute"):
            return

        await member.timeout(None, reason=f"{ctx.author} | {reason}")
        await ctx.send(f"🔊 Unmuted {member.mention} • Reason: {reason}")

    @commands.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided.",
    ) -> None:
        if not await self._ensure_manageable(ctx, member, "warn"):
            return

        case_id = self._next_case_id()
        await self._send_punishment_dm(
            member=member,
            action="Warn",
            moderator=ctx.author,
            time_text="N/A",
            case_id=case_id,
            reason=reason,
        )
        await self._send_mod_log(
            guild=ctx.guild,
            target=member,
            action="Warn",
            moderator=ctx.author,
            time_text="N/A",
            case_id=case_id,
            reason=reason,
        )
        embed = discord.Embed(title="⚠️ Warning Issued", color=0xF1C40F)
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=str(case_id), inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        if message.author.guild_permissions.manage_messages:
            return

        now = message.created_at.timestamp()
        cache = self._recent_messages[message.author.id]
        cache.append(now)

        if len(cache) >= 6 and now - cache[0] <= 7:
            await message.channel.purge(limit=8, check=lambda m: m.author == message.author)
            await message.channel.send(
                f"🚫 {message.author.mention}, please stop spamming.",
                delete_after=6,
            )
            cache.clear()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
