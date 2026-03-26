import dotenv from "dotenv";
import express from "express";
import { createBot, registerCommands } from "./discord/bot.js";

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 3000);

const token = process.env.DISCORD_BOT_TOKEN;
const clientId = process.env.DISCORD_CLIENT_ID;
const guildId = process.env.DISCORD_GUILD_ID;

app.use(express.static("frontend"));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "nexohubbot", timestamp: new Date().toISOString() });
});

const start = async () => {
  if (!token || !clientId) {
    throw new Error("Missing DISCORD_BOT_TOKEN or DISCORD_CLIENT_ID in environment variables.");
  }

  const bot = createBot();

  await registerCommands({ token, clientId, guildId });
  await bot.login(token);

  app.listen(port, () => {
    console.log(`Backend + frontend server running on http://localhost:${port}`);
  });
};

start().catch((error) => {
  console.error("Failed to start NexoHub bot server", error);
  process.exit(1);
});
