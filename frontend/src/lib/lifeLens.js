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
