import { useCoinEdge } from './coinEdge';

// 🦠 THE GERM ON EVERY COIN — the agents' own chart read (1m + 5m real candles) carried on the shared coin edge record (`edge.germ`),
// no poller of its own. germ = the base candle of the coin's biggest run: its low is the floor that run was born on.
//   d = % the price sits above the 1m germ floor (negative = under it) · w floor | near | far | lost · e = the entry word
//   line = the owner's germ line (agentGermMax; 0 = off) · ok = inside it
export function useGerm(mint) {
  return useCoinEdge(mint)?.germ || null;
}

const n = v => (Number.isFinite(Number(v)) ? Number(v) : null);

// → { tone, word, short, tip, fill } or null (no read). tone: hot (on the floor, 5m agrees) · floor · near · far · lost
export function germView(g) {
  if (!g || n(g.d) === null) return null;
  const d = n(g.d), line = n(g.line) || 0;
  const conf = g.e === 'confirmed';
  const tone = g.w === 'lost' || d < 0 ? 'lost' : conf ? 'hot' : g.w === 'floor' ? 'floor' : (line ? d <= line : g.w === 'near') ? 'near' : 'far';
  const where = d < 0 ? `${Math.abs(d).toFixed(0)}% under its germ floor` : `${d.toFixed(d < 10 ? 1 : 0)}% above its germ floor`;
  const word = { hot: 'ON THE GERM', floor: 'AT THE FLOOR', near: 'NEAR GERM', far: 'RAN OFF', lost: 'GERM LOST' }[tone];
  const short = d < 0 ? `−${Math.abs(d).toFixed(0)}%` : `+${d.toFixed(0)}%`;
  const tip = `🦠 ${word} · ${where}`
    + (n(g.d5) !== null ? ` · 5m ${n(g.d5) < 0 ? 'under' : `${n(g.d5).toFixed(0)}% above`} its floor${conf ? ' (agrees)' : ''}` : '')
    + (n(g.run) ? ` · the run it was born on: +${n(g.run).toFixed(0)}%` : '')
    + (line ? ` · ${g.ok ? 'inside' : 'outside'} your ${line}% germ line — the agents ${g.ok ? 'may buy it here' : 'won\'t buy it here'}` : '')
    + (tone === 'lost' ? ' · under the floor = the run is dead' : tone === 'far' ? ' · the move already ran (gun line)' : '');
  // fill: 1 on the floor → 0 at the line (how close to the germ), for the chip's meter
  const fill = d < 0 ? 0 : Math.max(0, Math.min(1, 1 - d / (line || 25)));
  return { tone, word, short, tip, fill, d };
}

// 🧠 WHY THE GERM MATTERS, for this coin right now (owner, 2026-10-19: "explain to users simply why the germ is vital with realtime data").
// Three plain lines from the coin's own read + the replay we ran (233 pools, 1m candles, after a 3% round trip: entries on the germ reached
// +10% within 30 min 27% of the time vs 9% for gun-line breakouts). A read, never a promise.
export const GERM_PROOF = { at: 27, gun: 9, pools: 233 };
export function germWhy(g) {
  const v = germView(g); if (!v) return null;
  const d = v.d; const run = n(g.run);
  const risk = d < 0 ? 'it already broke the floor its run was born on — the move is dead until it builds a new one'
    : d <= 8 ? `your stop can sit just under the floor: only about ${Math.max(1, Math.round(d + 3))}% of room to lose`
      : d <= 25 ? `about ${Math.round(d)}% above the floor — a stop under it costs that much if it fails`
        : `${Math.round(d)}% above the floor — buying here is buying the run, not its birth (the gun line)`;
  return { ...v, lines: [
    `🦠 The germ is the candle a run was BORN on${run ? ` (this one ran +${Math.round(run)}%)` : ''}. Smart money defends that floor.`,
    `📍 Right now ${$sym(g)} is ${d < 0 ? `${Math.abs(d).toFixed(0)}% UNDER` : `${d.toFixed(d < 10 ? 1 : 0)}% above`} it${n(g.d5) !== null ? `, the 5-minute chart ${n(g.d5) >= 0 && Math.abs(n(g.d5)) <= 15 ? 'agrees' : 'does not agree'}` : ''} — ${risk}.`,
    `📊 On our replay of ${GERM_PROOF.pools} pools, entries on the germ hit +10% ${GERM_PROOF.at}% of the time vs ${GERM_PROOF.gun}% for buying the breakout — they also dip harder first, so it's the upside, not a sure thing.`,
  ] };
}
const $sym = g => (g && g.sym ? `$${g.sym}` : 'the price');
