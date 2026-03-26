from __future__ import annotations

import asyncio
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import discord
from discord import app_commands
from discord.ext import commands


@dataclass
class VerificationState:
    user_id: int
    token: str
    target: int
    counter_a: int = 0
    counter_b: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "target": self.target,
            "counter_a": self.counter_a,
            "counter_b": self.counter_b,
            "started_at": self.started_at.isoformat(),
        }


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
        self._public_base_url = os.getenv("WEB_PANEL_PUBLIC_URL", "").rstrip("/")

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

    def _state_by_token(self, token: str) -> VerificationState | None:
        for state in self.verifications.values():
            if state.token == token:
                return state
        return None

    def _remove_verification(self, user_id: int) -> None:
        if user_id in self.verifications:
            del self.verifications[user_id]

    def _apply_action(self, state: VerificationState, action: str) -> str | None:
        if action == "inc_a":
            state.counter_a += 1
        elif action == "inc_b":
            state.counter_b += 1
        elif action == "reset":
            state.counter_a = 0
            state.counter_b = 0
            self.total_resets += 1

        if state.counter_a > state.target or state.counter_b > state.target:
            self.total_failures += 1
            self._remove_verification(state.user_id)
            return "❌ Verification failed (counter exceeded target). Run /verify-start again."

        if state.counter_a == state.target and state.counter_b == state.target:
            self.total_completed += 1
            self.verified_users.add(state.user_id)
            self._remove_verification(state.user_id)
            return "✅ Verification complete. You can return to Discord."

        return None

    def _verification_page(
        self,
        *,
        token: str,
        state: VerificationState | None,
        status: str | None = None,
    ) -> str:
        if state is None:
            return """
<!doctype html>
<html><body style='font-family:Arial;background:#0e1117;color:#e6edf3;padding:2rem;'>
<h1>Verification Session Not Found</h1>
<p>This session is expired or invalid. Run <strong>/verify-start</strong> again in Discord.</p>
</body></html>
"""

        status_html = f"<p><strong>{status}</strong></p>" if status else ""
        return f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Double Counter Verification</title>
    <style>
      body {{ font-family: Arial, sans-serif; background: #0e1117; color: #e6edf3; margin: 2rem; }}
      .card {{ background: #161b22; border-radius: 12px; padding: 1rem; max-width: 520px; }}
      .counter {{ display: inline-block; min-width: 90px; font-size: 2rem; font-weight: 700; }}
      .row {{ margin: 1rem 0; display:flex; justify-content:space-between; align-items:center; }}
      .actions {{ display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 1rem; }}
      a.button {{ text-decoration: none; color: #fff; background: #238636; padding: 0.6rem 0.9rem; border-radius: 8px; }}
      a.secondary {{ background: #30363d; }}
      .muted {{ color: #8b949e; }}
    </style>
  </head>
  <body>
    <div class='card'>
      <h1>Double Counter</h1>
      <p class='muted'>Match both counters to the target exactly.</p>
      {status_html}
      <div class='row'><span>Target</span><span class='counter'>{state.target}</span></div>
      <div class='row'><span>Counter A</span><span class='counter'>{state.counter_a}</span></div>
      <div class='row'><span>Counter B</span><span class='counter'>{state.counter_b}</span></div>
      <div class='actions'>
        <a class='button' href='/verify/{token}?action=inc_a'>Counter A +1</a>
        <a class='button' href='/verify/{token}?action=inc_b'>Counter B +1</a>
        <a class='button secondary' href='/verify/{token}?action=reset'>Reset</a>
      </div>
    </div>
  </body>
</html>
"""

    async def _handle_http_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(4096)
        request_line = data.decode("utf-8", errors="ignore").splitlines()
        method = "GET"
        path = "/"
        if request_line:
            parts = request_line[0].split(" ")
            if len(parts) >= 3:
                method = parts[0].upper()
                path = parts[1]

        if path == "/api/status":
            body = json.dumps(self._panel_payload(), indent=2)
            content_type = "application/json"
        elif path.startswith("/verify/") and method == "GET":
            parsed = urlparse(path)
            token = parsed.path.removeprefix("/verify/").strip("/")
            query = parse_qs(parsed.query)
            action = query.get("action", [None])[0]
            state = self._state_by_token(token)
            status = None
            if state and action:
                status = self._apply_action(state, action)
                state = self._state_by_token(token)

            body = self._verification_page(token=token, state=state, status=status)
            content_type = "text/html; charset=utf-8"
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
        state = VerificationState(
            user_id=interaction.user.id,
            token=secrets.token_hex(12),
            target=target,
        )
        self.verifications[interaction.user.id] = state
        self.total_started += 1

        if self._public_base_url:
            verification_url = f"{self._public_base_url}/verify/{state.token}"
        else:
            verification_url = f"http://localhost:{self._port}/verify/{state.token}"

        await interaction.response.send_message(
            content=(
                "Double Counter Verification started.\n"
                f"Open this link and complete the challenge: {verification_url}\n"
                f"Target: **{target}**\n"
                "You must match both counters to the target exactly."
            ),
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
