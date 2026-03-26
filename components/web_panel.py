from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands


@dataclass
class VerificationState:
    token: str
    target: int
    counter_a: int = 0
    counter_b: int = 0
    started_at: datetime = datetime.now(timezone.utc)

    def as_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "target": self.target,
            "counter_a": self.counter_a,
            "counter_b": self.counter_b,
            "started_at": self.started_at.isoformat(),
        }


class VerificationView(discord.ui.View):
    def __init__(self, cog: "WebPanelVerification", user_id: int) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

    async def _update_progress(
        self,
        interaction: discord.Interaction,
        lane: str | None,
        *,
        reset: bool = False,
    ) -> None:
        state = self.cog.verifications.get(self.user_id)
        if state is None:
            await interaction.response.send_message(
                "No active verification session found. Run /verify-start again.",
                ephemeral=True,
            )
            return

        if reset:
            state.counter_a = 0
            state.counter_b = 0
            self.cog.total_resets += 1
        elif lane == "a":
            state.counter_a += 1
        elif lane == "b":
            state.counter_b += 1

        if state.counter_a > state.target or state.counter_b > state.target:
            self.cog.total_failures += 1
            del self.cog.verifications[self.user_id]
            await interaction.response.edit_message(
                content=(
                    "❌ Verification failed (counter exceeded target). "
                    "Run /verify-start to try again."
                ),
                view=None,
            )
            return

        if state.counter_a == state.target and state.counter_b == state.target:
            self.cog.total_completed += 1
            self.cog.verified_users.add(self.user_id)
            del self.cog.verifications[self.user_id]
            await interaction.response.edit_message(
                content="✅ Verification complete! Double counter reached target on both lanes.",
                view=None,
            )
            return

        await interaction.response.edit_message(
            content=(
                f"Double Counter Verification\n"
                f"Target: **{state.target}**\n"
                f"Counter A: **{state.counter_a}**\n"
                f"Counter B: **{state.counter_b}**"
            ),
            view=self,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the user who started this verification can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Counter A +1", style=discord.ButtonStyle.primary)
    async def counter_a_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self._update_progress(interaction, "a")

    @discord.ui.button(label="Counter B +1", style=discord.ButtonStyle.success)
    async def counter_b_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self._update_progress(interaction, "b")

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.secondary)
    async def reset_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        await self._update_progress(interaction, None, reset=True)


class WebPanelVerification(commands.Cog):
    """Hosts a small web panel and a double-counter verification flow."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.verifications: dict[int, VerificationState] = {}
        self.verified_users: set[int] = set()
        self.total_started = 0
        self.total_completed = 0
        self.total_failures = 0
        self.total_resets = 0
        self._server: asyncio.base_events.Server | None = None
        self._host = "0.0.0.0"
        self._port = 8080

    async def cog_load(self) -> None:
        self._server = await asyncio.start_server(self._handle_http_client, self._host, self._port)

    async def cog_unload(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    def _panel_payload(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self.verifications),
            "verified_users": len(self.verified_users),
            "total_started": self.total_started,
            "total_completed": self.total_completed,
            "total_failures": self.total_failures,
            "total_resets": self.total_resets,
            "active": [
                {
                    "user_id": user_id,
                    **state.as_dict(),
                }
                for user_id, state in self.verifications.items()
            ],
        }

    async def _handle_http_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(4096)
        request_line = data.decode("utf-8", errors="ignore").splitlines()
        path = "/"
        if request_line:
            parts = request_line[0].split(" ")
            if len(parts) >= 2:
                path = parts[1]

        if path == "/api/status":
            body = json.dumps(self._panel_payload(), indent=2)
            content_type = "application/json"
        else:
            stats = self._panel_payload()
            rows = "".join(
                "<tr>"
                f"<td>{row['user_id']}</td>"
                f"<td>{row['target']}</td>"
                f"<td>{row['counter_a']}</td>"
                f"<td>{row['counter_b']}</td>"
                f"<td>{row['started_at']}</td>"
                "</tr>"
                for row in stats["active"]
            )
            if not rows:
                rows = "<tr><td colspan='5'>No active sessions</td></tr>"
            body = f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>NexoHub Verification Panel</title>
    <style>
      body {{ font-family: Arial, sans-serif; background: #0e1117; color: #e6edf3; margin: 2rem; }}
      .card {{ background: #161b22; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border-bottom: 1px solid #30363d; padding: 0.6rem; text-align: left; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 0.7rem; }}
      .muted {{ color: #8b949e; }}
    </style>
  </head>
  <body>
    <h1>NexoHub Web Panel</h1>
    <p class='muted'>Double counter verification dashboard • refreshes every 6 seconds.</p>
    <div class='grid'>
      <div class='card'><strong>Active Sessions</strong><br>{stats['active_sessions']}</div>
      <div class='card'><strong>Verified Users</strong><br>{stats['verified_users']}</div>
      <div class='card'><strong>Total Started</strong><br>{stats['total_started']}</div>
      <div class='card'><strong>Total Completed</strong><br>{stats['total_completed']}</div>
      <div class='card'><strong>Total Failures</strong><br>{stats['total_failures']}</div>
      <div class='card'><strong>Total Resets</strong><br>{stats['total_resets']}</div>
    </div>
    <div class='card'>
      <h2>Active Verification Sessions</h2>
      <table>
        <thead>
          <tr><th>User ID</th><th>Target</th><th>Counter A</th><th>Counter B</th><th>Started At (UTC)</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <script>setTimeout(() => window.location.reload(), 6000);</script>
  </body>
</html>
"""
            content_type = "text/html; charset=utf-8"

        response = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n"
            f"{body}"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    @app_commands.command(name="verify-start", description="Start double-counter verification.")
    async def verify_start(self, interaction: discord.Interaction) -> None:
        target = secrets.randbelow(3) + 2  # target range 2-4 inclusive
        state = VerificationState(token=secrets.token_hex(6), target=target)
        self.verifications[interaction.user.id] = state
        self.total_started += 1

        view = VerificationView(self, interaction.user.id)
        await interaction.response.send_message(
            content=(
                "Double Counter Verification\n"
                f"Target: **{target}**\n"
                "Press Counter A and Counter B buttons until both match the target exactly.\n"
                "If either counter exceeds target, verification fails."
            ),
            view=view,
            ephemeral=True,
        )

    @app_commands.command(name="verify-status", description="See your verification status.")
    async def verify_status(self, interaction: discord.Interaction) -> None:
        if interaction.user.id in self.verified_users:
            await interaction.response.send_message(
                "✅ You are fully verified in the double-counter system.",
                ephemeral=True,
            )
            return

        state = self.verifications.get(interaction.user.id)
        if state is None:
            await interaction.response.send_message(
                "No active verification session. Use /verify-start.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            (
                f"In progress • Target {state.target} • "
                f"Counter A {state.counter_a} • Counter B {state.counter_b}"
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebPanelVerification(bot))
