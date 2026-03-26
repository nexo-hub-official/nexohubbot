# NexoHubBot (Node.js)

This project has been migrated from Python to a Node.js stack while keeping the existing `venv/` directory untouched.

## Stack
- **Backend**: Express (`backend/src/server.js`)
- **Discord Bot**: `discord.js` (`backend/src/discord/bot.js`)
- **Frontend**: Static dashboard (`frontend/`)

## Environment variables
Create a `.env` file with:

```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_application_client_id
# Optional (recommended for fast slash command propagation)
DISCORD_GUILD_ID=your_test_guild_id
PORT=3000
```

## Run
```bash
npm install
npm start
```

Open `http://localhost:3000` for the frontend dashboard.
