// 🗂 ONE FOLDER PER GAME (owner 2026-11-15: "if I refile the same proof it just adds on to the current … not apart of the one PoB folder").
// Every run on the same game sits as a file inside one PoB folder: "Thunder vs Kings" and "Thunder vs Kings team to win" are one folder.
const SKIP = new Set(['vs', 'v', 'at', 'versus', 'and', 'the', 'a', 'an', 'of', 'on', 'for', 'team', 'to', 'win', 'wins', 'parlay', 'parlays', 'slip', 'sgp',
  'leg', 'legs', 'pick', 'picks', 'best', 'tonight', 'today', 'game', 'games', 'bid', 'bids', 'moneyline', 'ml', 'straight', 'winner', 'pob', 'test', 'this', 'file', 'make', 'start']);

export function pobKey(x) {
  const t = String(x?.topic || x?.q || '').toLowerCase().split(/[.:]/)[0];   // "file a pob X. Test this: …" keeps only the game
  const words = [...new Set((t.match(/[a-z0-9]+/g) || []).filter(w => !SKIP.has(w) && !/^\d+$/.test(w)))].sort();
  return words.length ? words.join(' ') : `run:${x?.id}`;
}

// → [{ key, head (newest run), runs (newest first) }], newest folder first. A run with no topic (the free-chip board) is its own folder.
export function pobGroups(rows) {
  const by = new Map();
  for (const x of rows || []) {
    const k = pobKey(x);
    if (!by.has(k)) by.set(k, []);
    by.get(k).push(x);
  }
  return [...by.entries()].map(([key, runs]) => ({ key, head: runs[0], runs }));
}

// What the run was, in two words: its mode, or how it ended.
export function runLabel(x) {
  const t = String(x?.topic || '').toLowerCase();
  const mode = /\b(parlay|slip|legs?)\b/.test(t) ? 'Parlay slip' : /\b(team to win|moneyline|to win)\b/.test(t) ? 'Team to win' : '';
  const k = x?.kalshi;
  const money = k?.orderId ? (k.outcome ? `Kalshi ${k.outcome === 'won' ? 'WON' : 'lost'}` : 'Real bid placed') : k?.status === 'waiting' ? 'Waiting for your tap' : '';
  return [mode, money].filter(Boolean).join(' · ') || (x?.graded ? `Marked ${x.graded}` : x?.status !== 'closed' ? 'Running' : 'Filed');
}
