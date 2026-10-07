// ✋ GRAB YOUR LEVELS: on a Fuse coin's chart the card's stop / take-profit / lock / trail lines can be dragged. A drag never
// free-types a number: it snaps to the SAME options the card's editor offers (= arena_prime LEG_SLS / LEG_TPS / RIDE_ATS /
// RIDE_TRAILS — change both). stop + tp are this COIN's own; lock + trail are the CARD's (every coin) and say so.
export const GRAB = {
  stop: { ic: '🛑', name: 'stop', list: [10, 15, 20, 30], sign: -1, base: 'entry', scope: 'coin' },
  tp: { ic: '🎯', name: 'take-profit', list: [25, 50, 100, 200, 300], sign: 1, base: 'entry', scope: 'coin' },
  lock: { ic: '❄', name: 'lock', list: [10, 15, 20, 25, 50, 100, 150], sign: 1, base: 'entry', scope: 'card' },
  trail: { ic: '🏔', name: 'trail', list: [5, 8, 10, 15, 20, 30], sign: -1, base: 'peak', scope: 'card' },
};
const priceAt = (g, base, pct) => base * (1 + g.sign * pct / 100);

// the option nearest to where the line was dropped → { pct, price }
export function snapLevel(kind, price, base) {
  const g = GRAB[kind]; if (!g || !(base > 0) || !(price > 0)) return null;
  const want = g.sign * (price / base - 1) * 100;
  const pct = g.list.reduce((a, b) => (Math.abs(b - want) < Math.abs(a - want) ? b : a), g.list[0]);
  return { pct, price: priceAt(g, base, pct) };
}

// which lines of this Fuse coin can be grabbed right now: riding → its trail; else its stop + lock (or take-profit when the card has no lock)
export function grabLevels(f) {
  if (!f?.tpl || !(f.entry > 0)) return [];
  const row = (kind, pct, from) => ({ ...GRAB[kind], kind, pct, from, price: priceAt(GRAB[kind], from, pct) });   /* `from` = the price the % counts from (entry, or the peak for a trail) */
  if (f.riding) return f.peak > 0 && f.trailPct > 0 ? [row('trail', f.trailPct, f.peak)] : [];
  const out = [];
  if (f.slPct > 0) out.push(row('stop', f.slPct, f.entry));
  if (f.lockPct > 0) out.push(row('lock', f.lockPct, f.entry)); else if (f.tpPct > 0) out.push(row('tp', f.tpPct, f.entry));
  return out;
}

// the Fuse levels after a confirmed drag (so the lines sit where they were dropped until the card's next read)
export function withGrab(f, ov) {
  if (!f || !ov) return f; const o = { ...f };
  if (ov.stop) { o.slPct = ov.stop; if (!o.riding) o.stop = priceAt(GRAB.stop, o.entry, ov.stop); }
  if (ov.tp) o.tpPct = ov.tp;
  if (ov.lock) { o.lockPct = ov.lock; if (!o.riding) o.lock = priceAt(GRAB.lock, o.entry, ov.lock); }
  if (ov.trail) { o.trailPct = ov.trail; if (o.riding && o.peak > 0) o.trail = priceAt(GRAB.trail, o.peak, ov.trail); }
  return o;
}

// the admin body + plain words for a dropped level (HqRealCards confirms, then posts)
export function grabOrder(d) {
  const g = GRAB[d?.kind]; if (!g || !d.tpl || !d.pairAddress || !g.list.includes(d.pct)) return null; const s = `$${d.symbol || 'coin'}`;
  if (d.kind === 'stop') return { body: { leg: { tpl: d.tpl, pairAddress: d.pairAddress, sl: d.pct } }, ask: `Move ${s}'s stop to −${d.pct}% from its entry? Only this coin.`, ok: `🛑 ${s} stops at −${d.pct}%` };
  if (d.kind === 'tp') return { body: { leg: { tpl: d.tpl, pairAddress: d.pairAddress, tp: d.pct } }, ask: `Set ${s}'s take-profit to +${d.pct}% from its entry? Only this coin.`, ok: `🎯 ${s} takes profit at +${d.pct}%` };
  if (d.kind === 'lock') return { body: { realCfg: { rideAt: d.pct } }, ask: `Move the lock to +${d.pct}%? This is the CARD's setting: every coin on it locks at +${d.pct}% from now on.`, ok: `❄ Coins lock at +${d.pct}%` };
  return { body: { realCfg: { rideTrail: d.pct } }, ask: `Move the trail to ${d.pct}% off the peak? This is the CARD's setting: every locked coin on it trails by ${d.pct}%.`, ok: `🏔 Locked coins trail ${d.pct}% off their peak` };
}
