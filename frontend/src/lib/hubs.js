// 12 entries, not 18: related pages share ONE sidebar entry and switch with hub tabs at the top (HubTabs). Every old URL still works.
export const HUBS = {
  pump: [['pump', '🚀 Pump radar'], ['launch', '🛰 Launchpads']],
  fee: [['fee', '💎 $FEE'], ['feeback', '♻ Fee-Back']],
  leaderboard: [['leaderboard', '🏆 Leaderboard'], ['badges', '🎖 Badges'], ['seasons', '👑 Seasons']],
  whitepaper: [['whitepaper', '📄 Whitepaper'], ['roadmap', '🗺 Roadmap'], ['learn', '📚 Learn']],
};
export const hubOf = page => Object.keys(HUBS).find(k => HUBS[k].some(([p]) => p === page)) || null;
