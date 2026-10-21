// 13 entries (🚀 Launch has its own since 2026-10-20 — the owner could not find it under Pump radar), not 18: related pages share ONE sidebar entry and switch with hub tabs at the top (HubTabs). Every old URL still works.
export const HUBS = {
  pump: [['pump', '🚀 Pump radar'], ['launch', '🚀 Launch']],
  fee: [['fee', '💎 $FEE'], ['feeback', '♻ Fee-Back']],
  leaderboard: [['leaderboard', '🌹 MOB & Rewards'], ['badges', '🎖 Badges'], ['seasons', '👑 Seasons']],
  whitepaper: [['whitepaper', '📄 Whitepaper'], ['roadmap', '🗺 Roadmap'], ['learn', '📚 Learn'], ['support', '🛟 Support']],
};
export const hubOf = page => Object.keys(HUBS).find(k => HUBS[k].some(([p]) => p === page)) || null;
