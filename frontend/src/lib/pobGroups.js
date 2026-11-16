// 🗂 ONE FILE PER GAME (owner 2026-11-15: "if I refile the same proof it just adds on to the current … one file shows but separate readings").
// Every PoB on the same real game is a READING inside one file. Same game = the same ESPN game id (whatever words he typed), or, before the
// scoreboard is known, the same teams named on the same day. A rematch on another day is a new file. backend/pob.py run_of mirrors this.
const SKIP = new Set(['vs', 'v', 'at', 'versus', 'and', 'the', 'a', 'an', 'of', 'on', 'for', 'team', 'to', 'win', 'wins', 'parlay', 'parlays', 'slip', 'sgp',
  'leg', 'legs', 'pick', 'picks', 'best', 'tonight', 'today', 'game', 'games', 'bid', 'bids', 'moneyline', 'ml', 'straight', 'winner', 'pob', 'test', 'this', 'file', 'make', 'start']);

export function pobKey(x) {
  const t = String(x?.topic || x?.q || '').toLowerCase().split(/[.:]/)[0];   // "file a pob X. Test this: …" keeps only the game
  return [...new Set((t.match(/[a-z0-9]+/g) || []).filter(w => !SKIP.has(w) && !/^\d+$/.test(w)))].sort().join(' ');
}
const ids = x => new Set((x?.games || []).map(g => String(g?.id || '')).filter(Boolean));
const day = x => (x?.at ? new Date(x.at * 1000).toDateString() : '');

// Two PoBs are readings of one file when they are about the same real game.
export function sameGame(a, b) {
  const ka = pobKey(a); const kb = pobKey(b); if (!ka || !kb) return false;   // no topic (the free-chip board) is always a file of its own
  const ia = ids(a); const ib = ids(b);
  if (ia.size && ib.size) return [...ia].some(i => ib.has(i)) && (ka === kb || (ia.size === ib.size && [...ia].every(i => ib.has(i))));
  return ka === kb && day(a) === day(b);
}

// rows newest first → [{ key (its first reading's id: stable as readings land), head (newest reading), runs (newest first) }], newest file first.
export function pobGroups(rows) {
  const all = rows || []; let out = [];
  for (const x of all) {   // a reading joins every file it matches, and those files become one (OKC Sacramento + Thunder vs Kings + the slip)
    const hit = out.filter(o => o.some(r => sameGame(r, x)));
    out = [...out.filter(o => !hit.includes(o)), [...hit.flat(), x]];
  }
  const at = x => all.indexOf(x);
  return out.map(g => g.sort((a, b) => at(a) - at(b))).sort((a, b) => at(a[0]) - at(b[0])).map(runs => ({ head: runs[0], runs, key: runs[runs.length - 1].id }));
}

// The game's name, without the mode words: "Thunder vs Kings team to win" → "Thunder vs Kings".
export const gameName = x => String(x?.topic || x?.q || 'PoB').split(/[.:]/)[0].replace(/^\s*(file|make|start)\s+(a\s+)?pob\s+(on\s+)?/i, '').replace(/\b(team to win|parlay slip|parlay)\b/ig, '').replace(/\s+/g, ' ').trim();

// What a reading was, in a few words: its mode, and how it ended.
export function runLabel(x) {
  const t = String(x?.topic || '').toLowerCase();
  const mode = /\b(parlay|slip|legs?)\b/.test(t) ? 'Parlay slip' : /\b(team to win|moneyline|to win)\b/.test(t) ? 'Team to win' : '';
  const k = x?.kalshi;
  const money = k?.orderId ? (k.outcome ? `Kalshi ${k.outcome === 'won' ? 'WON' : 'lost'}` : 'Real bid placed') : k?.status === 'waiting' ? 'Waiting for your tap' : '';
  return [mode, money].filter(Boolean).join(' · ') || (x?.graded ? `Marked ${x.graded}` : x?.status !== 'closed' ? 'Running' : 'Filed');
}
