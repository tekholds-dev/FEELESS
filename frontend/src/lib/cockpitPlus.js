// 🧩 Cockpit add-ons (owner, 2026-10-16): ✂ would-sell ghosts on the chart · 🩸 a small rug marker when a held coin's pool starts draining ·
// 💎 diamond-hands score · 🔁 G4 vs OSSY league · 🧠 Brain answers as cards · 🎞 a seat's ride as a share card. Pure — every number comes
// from the Agents payload; nothing here fetches.
const num = v => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const sgn = v => `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`;

// ✂ where the agents WOULD have sold your pick, as chart markers at that price (entry × (1 + pct))
export function ghostMarkers(pos) {
  const en = num(pos?.entry); if (!en) return [];
  return (pos?.ghosts || []).filter(g => num(g.at) && num(g.pct) != null).map(g => ({
    time: Math.floor(num(g.at)), position: 'atPriceTop', price: en * (1 + num(g.pct) / 100), shape: 'circle', color: '#b79bff', text: '✂',
    id: `g${g.at}`, agent: 'reaper', action: `WOULD SELL ${sgn(g.pct)}`, why: `${g.rule || 'an agent rule'} would have sold here — you held`, at: num(g.at) }));
}

// 🩸 the rug marker: the moment a held coin's pool starts draining (Reaper's drain read, or the pool ≥ 15% under its depth at entry)
export function rugMark(s) {
  if (!s || s.open) return null;
  const st = s.drain?.state; const lp = num(s.liqPct);
  if (st === 'DRAIN') return { level: 'bad', why: `pool draining — ${(s.drain.why || []).join(' · ') || `score ${s.drain.score}`}` };
  if (lp != null && lp <= 70) return { level: 'bad', why: `pool at ${lp}% of its depth at entry` };
  if (st === 'WATCH') return { level: 'warn', why: `pool thinning — ${(s.drain.why || []).join(' · ') || 'drain watch'}` };
  if (lp != null && lp <= 85) return { level: 'warn', why: `pool at ${lp}% of its depth at entry` };
  return null;
}

// 💎 diamond hands: on YOUR closed trades, what holding past the agents' FIRST would-sell made or lost (result − that %)
export function diamondOf(rows) {
  const xs = (rows || []).filter(r => r.who === 'you' && !r.open && num(r?.result?.pct) != null && num(r?.replay?.would?.[0]?.pct) != null)
    .map(r => ({ sym: r.sym || '?', mint: r.mint, end: num(r.result.pct), would: num(r.replay.would[0].pct), gain: num(r.result.pct) - num(r.replay.would[0].pct) }));
  if (!xs.length) return { n: 0 };
  const total = xs.reduce((a, x) => a + x.gain, 0); const best = xs.reduce((a, x) => (x.gain > a.gain ? x : a), xs[0]); const worst = xs.reduce((a, x) => (x.gain < a.gain ? x : a), xs[0]);
  return { n: xs.length, won: xs.filter(x => x.gain > 0).length, avg: total / xs.length, best, worst };
}

// 🔁 the G4 vs OSSY league from the duo block: who leads on typical result (then win %), with a word for it
export function leagueOf(duo) {
  const r = duo?.rec || {}; const a = r.G4 || { n: 0 }; const b = r.OSSY || { n: 0 };
  if (!a.n && !b.n) return { lead: null, word: 'no closed paper trades yet', a, b };
  const score = x => (x.n ? (num(x.med) || 0) * 10 + (num(x.won) || 0) / 10 : -1e9);
  const lead = score(a) === score(b) ? null : score(a) > score(b) ? 'G4' : 'OSSY';
  return { lead, word: lead ? `${lead} leads` : 'dead even', a, b };
}

// 🧠 a Brain answer as a card: the headline (first sentence with a number, else the first), ≤ 3 bullets, the $COINS it names
export function answerCard(text) {
  const t = String(text || '').replace(/\s+/g, ' ').trim();
  if (!t) return null;
  const body = t.split(/\bsources?:/i)[0].trim();
  const sents = body.split(/(?<=[.!?])\s+(?=[A-Z0-9$"'(])/).map(s => s.trim()).filter(Boolean);
  if (sents.length < 2 && body.length < 160) return null;   // a short reply stays a plain line
  const hi = sents.findIndex(s => /[$%]\s?\d|\d\s?%|\d+(\.\d+)?x\b|\+\d|−\d|-\d/.test(s));
  const head = sents[hi >= 0 ? hi : 0];
  const bullets = sents.filter(s => s !== head).slice(0, 3);
  const coins = [...new Set((body.match(/\$[A-Za-z][A-Za-z0-9]{1,11}\b/g) || []).map(c => c.slice(1).toUpperCase()))].slice(0, 4);
  return { head, bullets, coins, more: Math.max(0, sents.length - 1 - bullets.length) };
}

// 🎞 a seat's ride as a share card (entry → now, peak, the agents' first would-sell, how long it was held)
export function rideCard(s, pos) {
  if (!s || s.open) return null;
  const pct = num(s.pct); const peak = num(s.peak); const g = (pos?.ghosts || [])[0];
  return { title: `$${s.symbol} ride`, bigValue: pct ?? 0, bigPrefix: pct >= 0 ? '+' : '', bigSuffix: '%', bigDigits: 1, bigSub: s.pnlUsd != null ? `${s.pnlUsd >= 0 ? '+' : '−'}$${Math.abs(s.pnlUsd).toFixed(2)}` : '',
    tone: pct >= 0 ? 'up' : 'down', theme: pct >= 50 ? 'gold' : 'royal',
    lines: [s.kind === 'yours' ? 'your pick — held through the noise' : 'held by the FEELESS agents', g ? `agents would have sold at ${sgn(g.pct)} (${g.rule})` : 'no early exit call', ''],
    stats: [{ label: 'entry mc', value: s.entryMc ? `$${Math.round(s.entryMc / 1000)}K` : '—' }, { label: 'now mc', value: s.mc ? `$${Math.round(s.mc / 1000)}K` : '—' },
      { label: 'peak', value: peak != null ? sgn(peak) : '—', tone: 'ok' }, { label: 'held', value: s.heldMin != null ? `${Math.round(s.heldMin)} min` : '—' }],
    footer: 'feeless · fuse agents' };
}
