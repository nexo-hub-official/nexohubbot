import {
  Client,
  Events,
  GatewayIntentBits,
  REST,
  Routes,
  SlashCommandBuilder
} from "discord.js";
import { MANAGEMENT_ROLE_IDS, PRIVILEGED_ROLE_IDS, ROLE_IDS } from "../config/roles.js";

const commands = [
  new SlashCommandBuilder().setName("ping").setDescription("Check if the bot is online."),
  new SlashCommandBuilder()
    .setName("syncstaffrole")
    .setDescription("Add the staff team role to members who have staff permissions roles.")
].map((cmd) => cmd.toJSON());

const memberHasAnyRole = (member, allowedRoleIds) =>
  member.roles.cache.some((role) => allowedRoleIds.has(role.id));

const ensureStaffTeamRole = async (member) => {
  if (!member.guild) {
    return false;
  }

  const hasPrivilegedRole = memberHasAnyRole(member, PRIVILEGED_ROLE_IDS);
  if (!hasPrivilegedRole || member.roles.cache.has(ROLE_IDS.staffTeam)) {
    return false;
  }

  const staffTeamRole = member.guild.roles.cache.get(ROLE_IDS.staffTeam);
  if (!staffTeamRole) {
    return false;
  }

  await member.roles.add(staffTeamRole, "Auto-added for staff permissions");
  return true;
};

export const createBot = () => {
  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMembers,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent
    ]
  });

  client.once(Events.ClientReady, (readyClient) => {
    console.log(`Bot online as ${readyClient.user.tag}`);
  });

  client.on(Events.GuildMemberAdd, async (member) => {
    await ensureStaffTeamRole(member);
  });

  client.on(Events.GuildMemberUpdate, async (before, after) => {
    const beforeRoleIds = new Set(before.roles.cache.keys());
    const afterRoleIds = new Set(after.roles.cache.keys());
    if (beforeRoleIds.size === afterRoleIds.size && [...beforeRoleIds].every((id) => afterRoleIds.has(id))) {
      return;
    }

    await ensureStaffTeamRole(after);
  });

  client.on(Events.InteractionCreate, async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === "ping") {
      await interaction.reply({ content: "Pong! 🏓", ephemeral: true });
      return;
    }

    if (interaction.commandName === "syncstaffrole") {
      if (!interaction.inGuild()) {
        await interaction.reply({
          content: "This command can only be used inside a server.",
          ephemeral: true
        });
        return;
      }

      const member = interaction.member;
      if (!member || !member.roles || !memberHasAnyRole(member, MANAGEMENT_ROLE_IDS)) {
        await interaction.reply({
          content: "You do not have permission to run this command.",
          ephemeral: true
        });
        return;
      }

      const staffTeamRole = interaction.guild.roles.cache.get(ROLE_IDS.staffTeam);
      if (!staffTeamRole) {
        await interaction.reply({
          content: "Staff Team role is missing. Verify the role ID in backend/src/config/roles.js.",
          ephemeral: true
        });
        return;
      }

      await interaction.deferReply({ ephemeral: true });

      let changed = 0;
      const members = await interaction.guild.members.fetch();
      for (const guildMember of members.values()) {
        const hasPrivilegedRole = memberHasAnyRole(guildMember, PRIVILEGED_ROLE_IDS);
        if (hasPrivilegedRole && !guildMember.roles.cache.has(ROLE_IDS.staffTeam)) {
          await guildMember.roles.add(staffTeamRole, "Manual /syncstaffrole run");
          changed += 1;
        }
      }

      await interaction.editReply(`Done. Added ${staffTeamRole.toString()} to ${changed} member(s).`);
    }
  });

  return client;
};

export const registerCommands = async ({ token, clientId, guildId }) => {
  const rest = new REST({ version: "10" }).setToken(token);
  const route = guildId ? Routes.applicationGuildCommands(clientId, guildId) : Routes.applicationCommands(clientId);

  await rest.put(route, { body: commands });
  console.log(`Registered ${commands.length} slash command(s).`);
};
