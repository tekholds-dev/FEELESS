import { sharedJson } from './sharedJson';
import { useEffect, useRef, useState } from 'react';

// The lines a Fuse card draws on one coin's chart: entry, stop, lock (or the trail once it rides). Pure.
export const fuseLevels = (l, cf, label) => { const e = Number(l.entry) || 0; if (!(e > 0)) return null;
  const sl = Number(l.sl) || Number(cf?.sl) || 0; const ra = Number(cf?.rideAt) || 0; const tr = Number(cf?.rideTrail) || 0; const peak = Number(l.peak || l.high) || 0;
  return { card: label, pairAddress: l.pairAddress, symbol: l.symbol, entry: e, stop: sl > 0 && !l.ride ? e * (1 - sl / 100) : null, lock: ra > 0 && !l.ride ? e * (1 + ra / 100) : null,
    trail: l.ride && peak > 0 && tr > 0 ? peak * (1 - tr / 100) : null, riding: !!l.ride, slPct: sl, lockPct: ra, trailPct: tr, peak, tpPct: Number(l.tp) || 0 }; };

// Where a coin opened from a card stands on that card RIGHT NOW (pure): the war room used to keep the levels it was opened
// with, so after a 🔄 rebuy it still showed the old entry and stop and looked as if nothing had happened.
//   held → fresh levels · rebuying → sold, being bought back · buying → on the card, its buy not landed · gone → left the card
export function liveFuseFrom(d, snap) {
  if (!snap?.tpl || !snap.pairAddress) return { state: 'none', fuse: null };
  const c = (d?.cards || []).find(x => x.tpl === snap.tpl);
  if (!c) return { state: 'none', fuse: null };
  const l = (c.legs || []).find(x => x.pairAddress === snap.pairAddress);
  const mint = l?.mint || snap.mint;
  if (c.rebuying && (!mint || c.rebuying === mint)) return { state: 'rebuying', fuse: null };
  if (!l) return { state: (c.seatPick?.pairAddress === snap.pairAddress) ? 'rebuying' : 'gone', fuse: null };
  if (l.buying || !(Number(l.entry) > 0)) return { state: 'buying', fuse: null };
  return { state: 'held', fuse: { ...fuseLevels(l, c.cfgEff || d.cfg, c.label), tpl: c.tpl, mint: l.mint } };
}

// Live levels for the coin a chart was opened with from a card. Polls the card every 10s (every 3s for 2 minutes after `kick()`).
export function useLiveFuse(snap) {
  const [out, setOut] = useState({ state: 'none', fuse: null }); const fast = useRef(0);
  const tpl = snap?.tpl; const pair = snap?.pairAddress;
  useEffect(() => { if (!tpl || !pair) { setOut({ state: 'none', fuse: null }); return undefined; }
    let alive = true; let t;
    const load = () => sharedJson('/api/reputation/fuses/prime', { maxAge: 2500 }).then(d => alive && d && setOut(liveFuseFrom(d, { tpl, pairAddress: pair, mint: snap?.mint }))).catch(() => {})
      .finally(() => { if (alive) t = setTimeout(load, Date.now() < fast.current ? 3000 : 10000); });
    load(); return () => { alive = false; clearTimeout(t); }; }, [tpl, pair]);   // eslint-disable-line react-hooks/exhaustive-deps
  return { ...out, kick: () => { fast.current = Date.now() + 120000; } };
}
