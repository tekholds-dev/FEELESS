// 🧬 THE LIFE LENS — pure reads for the Generations pods, the rug wall and the creed (components/command/LifeLens.jsx).
// Every number comes from the payload; nothing here is a forecast.

const n = v => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));

// how close a generation is to being replaced: net = losses pinned − wins credited; replaced at `replaceAt` (≤ 0 = safe)
export function genRisk(g) {
  const net = n(g?.net); const at = n(g?.replaceAt) || 3; const pr = n(g?.probationAt) || Math.max(1, at - 1);
  if (net == null) return { frac: 0, word: 'NO RECORD', tone: 'is-calm' };
  const frac = Math.max(0, Math.min(1, net / at));
  return { frac, net, at, word: net >= at ? 'REPLACING' : net >= pr ? 'ON THE EDGE' : net > 0 ? 'SLIPPING' : 'SAFE', tone: net >= pr ? 'is-bad' : net > 0 ? 'is-warn' : 'is-good' };
}

// wins credited vs losses pinned as one split (null = nothing judged yet)
export function tug(g) {
  const w = n(g?.winsAttributed) || 0; const l = n(g?.lossesAttributed) || 0;
  return w + l ? { w, l, share: w / (w + l) } : null;
}

// one rug = one card: an open call and its judged copy are the same rug — keep the one that knows the 60-min result, newest first
export function dedupeAutopsies(list) {
  const by = new Map();
  (list || []).forEach(a => {
    const k = `${a?.sym}:${Math.round(n(a?.calledAt) || 0)}`;
    const cur = by.get(k);
    if (!cur || (cur.p60 == null && a.p60 != null)) by.set(k, a);
  });
  return [...by.values()].sort((a, b) => (n(b.calledAt) || 0) - (n(a.calledAt) || 0));
}

// "… — we read it as: a, b, c" → [a, b, c]
export const readAs = text => { const i = String(text || '').indexOf('we read it as:'); return i < 0 ? [] : String(text).slice(i + 14).split(/,\s*/).map(s => s.trim()).filter(Boolean).slice(0, 3); };

const MISSED = { band: 'cap band', pad: 'launchpad', chart: 'chart', strat: 'strategy', narr: 'narrative', src: 'found on' };
export function missedWord(key) {
  const k = String(key || ''); const i = k.indexOf(':');
  if (i < 0) return k.replace(/_/g, ' ');
  const head = MISSED[k.slice(0, i)] || k.slice(0, i); return `${head} ${k.slice(i + 1).replace(/_/g, ' ').toLowerCase()}`;
}

// a drop as a bar: |−68%| → 0.68 of the track
export const dropFrac = p => (n(p) == null ? 0 : Math.max(0, Math.min(1, Math.abs(n(p)) / 100)));

// 🧬 GENS v2 (owner, 2026-10-17: "each vital needs live realtime animation to see the good and bad in each agent and why he's better than
// older gens"). Pure reads of the lifecycle book: win rate now, the past generations' win rate, the edge between them, a timeline.
const rate = (w, l) => { const a = n(w) || 0; const b = n(l) || 0; return a + b ? Math.round((a / (a + b)) * 100) : null; };
export function winRate(g) { return rate(g?.winsAttributed, g?.lossesAttributed); }

export function genEdge(g) {
  const now = winRate(g);
  const past = (g?.lineage || []).map(p => ({ gen: p.gen, r: rate(p.wins, p.losses), n: (n(p.wins) || 0) + (n(p.losses) || 0) })).filter(p => p.r != null);
  if (now == null || !past.length) return { now, past: null, delta: null, word: now == null ? 'no real exits yet' : (g?.lineage || []).length ? 'older gens left no record' : 'first generation on record', tone: 'is-calm' };
  const tot = past.reduce((s, p) => s + p.n, 0); const avg = Math.round(past.reduce((s, p) => s + p.r * p.n, 0) / (tot || 1));
  const d = now - avg;
  return { now, past: avg, delta: d, word: d > 0 ? `+${d} pts better than gens ${past.map(p => p.gen).join(', ')}` : d < 0 ? `${d} pts worse than gens ${past.map(p => p.gen).join(', ')}` : 'level with its old gens', tone: d > 3 ? 'is-good' : d < -3 ? 'is-bad' : 'is-calm' };
}

export function genTimeline(g) {
  const past = [...(g?.lineage || [])].reverse().map(p => ({ gen: p.gen, r: rate(p.wins, p.losses), n: (n(p.wins) || 0) + (n(p.losses) || 0), why: p.cause || p.why, status: p.status, live: false }));
  return [...past, { gen: g?.generation, r: winRate(g), n: (n(g?.winsAttributed) || 0) + (n(g?.lossesAttributed) || 0), live: true }];
}

export function genBoard(gens) {
  const rows = (gens || []).map(g => ({ role: g.role, r: winRate(g), e: genEdge(g) })).filter(x => x.r != null);
  const best = [...rows].sort((a, b) => b.r - a.r)[0] || null;
  const up = [...rows].filter(x => x.e.delta != null).sort((a, b) => b.e.delta - a.e.delta)[0] || null;
  return { best, improved: up && up.e.delta > 0 ? up : null };
}
