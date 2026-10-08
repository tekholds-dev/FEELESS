import React, { useEffect, useState } from 'react';
import { useCoinEdge } from '../lib/coinEdge';
import { sharedJson } from '../lib/sharedJson';
import '../styles/rowVitals.css';

// One line of vitals under a coin in a pick list (Coming up, the swap picker): the launchpad it came from, age, cap, 1h volume,
// buyers, top-10 / dev / insiders when scanned, which socials it set, and the Pump radar (5m flow) from the shared coin edge.
// Only fields the row really has are shown — a missing one is left out, never a fake 0.
const big = v => { const n = Number(v); if (!(n > 0)) return null; return n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : `$${Math.round(n)}`; };
const age = h => (h == null || !Number.isFinite(Number(h)) ? null : h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)}h` : `${Math.round(h / 24)}d`);
const n0 = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));

// 🎯 the owner's own record by entry type (GET /fuses/my-edge, backend/owner_edge.py): one shared read
function useMyEdge() {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; sharedJson('/api/reputation/fuses/my-edge', { maxAge: 300000 }).then(x => alive && setD(x)).catch(() => {}); return () => { alive = false; }; }, []);
  return d;
}
const recTip = (rules, k) => { const r = rules?.[k]; return r && r.n >= 8 && r.pct != null ? `Your own picks like this: ${r.n} picks, ${r.wonPct}% won, ${r.pct >= 0 ? '+' : ''}${r.pct}% (price only, fees apart)` : ''; };

export function rowVitals(r, edge, mine) {
  const intel = edge?.intel || {}; const run = edge?.runner || {};
  const t10 = n0(r.top10) ?? n0(r.t10) ?? n0(intel.top10Pct); const dev = n0(r.dev) ?? n0(r.dh) ?? n0(intel.devHoldingPct); const ins = n0(r.insiders) ?? n0(intel.insidersHoldingPct);
  const buys = n0(r.buyShare) ?? n0(edge?.pulse?.buyShare);
  const out = [];
  if (r.pad) out.push({ k: 'pad', t: `🚀 ${r.pad}`, tip: 'The launchpad this coin came from' });
  if (age(r.ageH)) out.push({ k: 'age', t: age(r.ageH), tip: 'Age of the coin' });
  if (big(r.mcap)) out.push({ k: 'cap', t: `${big(r.mcap)} cap`, tip: 'Market cap' });
  if (big(r.vol1h)) out.push({ k: 'vol', t: `${big(r.vol1h)}/h`, tip: 'Traded in the last hour' });
  if (n0(r.holders)) out.push({ k: 'hold', t: `${Number(r.holders).toLocaleString()} holders`, tip: 'Wallets holding it' });
  if (buys != null) out.push({ k: 'buy', t: `${Math.round(buys)}% buys`, tone: buys >= 55 ? 'good' : buys < 45 ? 'bad' : '', tip: 'Share of recent trades that were buys' });
  if (t10 != null) out.push({ k: 't10', t: `top-10 ${Math.round(t10)}%`, tone: t10 > 30 ? 'bad' : t10 < 20 ? 'good' : '', tip: 'Supply held by the 10 biggest wallets (lower is safer)' });
  if (dev != null) out.push({ k: 'dev', t: `dev ${dev < 1 ? dev.toFixed(1) : Math.round(dev)}%`, tone: dev > 10 ? 'bad' : dev <= 3 ? 'good' : '', tip: 'Share the creator still holds' });
  if (ins != null) out.push({ k: 'ins', t: `insiders ${Math.round(ins)}%`, tone: ins > 15 ? 'bad' : ins < 5 ? 'good' : '', tip: 'Share held by wallets that were in at the start' });
  const bnd = n0(r.bundledN) ?? (r.scanned !== false && r.top10 != null ? n0(r.bundled) : null); const snp = n0(r.snipersN);
  if (bnd != null) out.push({ k: 'bnd', t: `${bnd} bundled`, tone: bnd > 1 ? 'bad' : bnd === 0 ? 'good' : '', tip: `Wallets that bought in the coin's creation slot${r.bundledPct != null ? ` — they still hold ${Number(r.bundledPct).toFixed(1)}%` : ''}` });
  if (snp != null) out.push({ k: 'snp-n', t: `${snp} snipers`, tone: snp > 10 ? 'bad' : snp <= 3 ? 'good' : '', tip: 'Wallets that bought within ~1 second of launch' });
  if (r.scanned === false && t10 == null) out.push({ k: 'scan', t: '🔍 holders not read yet', tip: 'Top-10, insiders and bundles are read from the chain; a scan is queued for the top of this list — they fill in within a minute or two' });
  const soc = [r.site && '🌐', r.x && '𝕏', r.tg && '✈'].filter(Boolean);
  if (r.site != null || r.x != null || r.tg != null) out.push({ k: 'soc', t: soc.length ? soc.join(' ') : 'no socials', tone: soc.length ? '' : 'bad', tip: 'Website · X · Telegram set at launch' });
  if (edge?.snipersOut) out.push({ k: 'snp', t: '🎯 snipers out', tone: 'good', tip: 'Every flagged sniper has sold out' });
  if (run.passing === false && run.gates?.[0]) out.push({ k: 'gate', t: `⚠ ${run.gates[0].split(' ').slice(0, 3).join(' ')}`, tone: 'bad', tip: run.gates.join(' · ') });
  const rules = mine?.rules;   // your own record on this kind of entry — shown as a chip, never a block
  if (r.chg5m != null && r.vol1h != null) {
    if (r.chg5m < -3 && r.vol1h >= 50000) out.push({ k: 'mine-setup', t: '✅ your setup', tone: 'good', tip: `A 5-minute dip with real volume. ${recTip(rules, 'setup')}` });
    else if (r.chg5m > 3) out.push({ k: 'mine-chase', t: '🔥 chasing', tone: 'bad', tip: `Up ${Number(r.chg5m).toFixed(1)}% in the last 5 minutes. ${recTip(rules, 'chase')}` });
  }
  if (r.liq > 0 && r.liq < 40000 && !r.trench) out.push({ k: 'mine-thinpool', t: '💧 thin pool', tone: 'bad', tip: `Pool under $40K — the card's real buys refuse it (12 of the last day's 15 crashes were pools this thin; a trench ticket keeps its own floor). ${recTip(rules, 'thinpool')}` });
  if (r.vol1h != null && r.vol1h < 20000) out.push({ k: 'mine-thin', t: '🪫 thin', tone: 'bad', tip: `Under $20K an hour. ${recTip(rules, 'thin')}` });
  const m5 = edge?.pulse?.m5Change;
  if (Number.isFinite(m5)) out.push({ k: 'radar', t: `📡 ${m5 >= 0 ? '+' : ''}${m5.toFixed(1)}% 5m`, tone: m5 >= 0 ? 'good' : 'bad', tip: 'Pump radar: the last 5 minutes of flow' });
  return out;
}

function Edged({ r, mine }) { const edge = useCoinEdge(r.mint); return <Line items={rowVitals(r, edge, mine)} />; }
function Line({ items }) { return items.length ? <span className="rv" data-testid="row-vitals">{items.map(i => <i key={i.k} className={`rv-c ${i.tone || ''}`} data-tip={i.tip}>{i.t}</i>)}</span> : null; }

// `live` = also read the shared coin edge (pulse, snipers, gates) — pass it for the rows on screen, not for a 300-row list.
export function RowVitals({ r, live = false }) {
  const mine = useMyEdge();
  if (!r) return null;
  return live && r.mint ? <Edged r={r} mine={mine} /> : <Line items={rowVitals(r, null, mine)} />;
}
