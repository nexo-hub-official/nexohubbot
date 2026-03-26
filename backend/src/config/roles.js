export const ROLE_IDS = {
  owner: "1475147779524268032",
  coowner: "1484442520967708773",
  botManager: "1486606070402125965",
  serverManager: "1483717313428717639",
  headAdministrator: "1483717311813914766",
  administrator: "1483717310257561640",
  trialAdministrator: "1486480724876984542",
  headModerator: "1483717307200180265",
  moderator: "1483717305312743455",
  trialModerator: "1483717303731490887",
  staffTeam: "1486481878172041327"
};

export const PRIVILEGED_ROLE_IDS = new Set([
  ROLE_IDS.owner,
  ROLE_IDS.coowner,
  ROLE_IDS.botManager,
  ROLE_IDS.serverManager,
  ROLE_IDS.headAdministrator,
  ROLE_IDS.administrator,
  ROLE_IDS.trialAdministrator,
  ROLE_IDS.headModerator,
  ROLE_IDS.moderator,
  ROLE_IDS.trialModerator
]);

export const MANAGEMENT_ROLE_IDS = new Set([
  ROLE_IDS.owner,
  ROLE_IDS.coowner,
  ROLE_IDS.botManager,
  ROLE_IDS.serverManager,
  ROLE_IDS.headAdministrator,
  ROLE_IDS.administrator
]);
