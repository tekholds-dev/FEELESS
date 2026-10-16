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
