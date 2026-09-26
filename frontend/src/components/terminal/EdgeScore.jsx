import React, { useEffect, useMemo, useState } from 'react';
import { Gauge } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { useReputation } from '../../lib/reputation';
import { AnimatedNumber } from './AnimatedNumber';

const clamp = v => Math.max(0, Math.min(100, v));
const n = v => (Number.isFinite(Number(v)) ? Number(v) : null);

function useIntel(pair) {
  const [intel, setIntel] = useState(null);
  const mint = pair?.chainId === 'solana' ? pair?.baseToken?.address : null;
  useEffect(() => {
    if (!mint || typeof fetch !== 'function') { setIntel(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/intel/solana/${mint}`)).then(r => (r.ok ? r.json() : null)).then(d => alive && setIntel(d)).catch(() => {});
    return () => { alive = false; };
  }, [mint]);
  return intel;
}

function useFeeRead(pair) {
  const [read, setRead] = useState(null);
  useEffect(() => {
    if (pair?.chainId !== 'solana' || !pair?.pairAddress || typeof fetch !== 'function') { setRead(null); return undefined; }
    let alive = true;
    fetch('/api/cats/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pairs: [{ chainId: 'solana', pairAddress: pair.pairAddress }] }) })
      .then(r => (r.ok ? r.json() : null)).then(d => alive && setRead(d?.reads?.[pair.pairAddress] || null)).catch(() => {});
    return () => { alive = false; };
  }, [pair?.chainId, pair?.pairAddress]);
  return read;
}

// FEELESS Edge Score: one 0–100 read from real, sourced signals. Missing signals are n/a and
// excluded from the weighting — never guessed.
export function computeEdge(pair, rep, intel, feeRead) {
  const f = [];
  const tx = pair?.txns?.h1 || {};
  const b = n(tx.buys) || 0; const s = n(tx.sells) || 0;
  f.push(['Order flow', 20, b + s >= 10 ? clamp(((b / (b + s)) - 0.35) / 0.3 * 100) : null, b + s >= 10 ? `${Math.round(b / (b + s) * 100)}% buys in the last hour (${b + s} trades)` : 'too few trades this hour']);
  const h1 = n(pair?.priceChange?.h1); const h6 = n(pair?.priceChange?.h6); const h24 = n(pair?.priceChange?.h24);
  let mom = null; let momWhy = 'no price history';
  if (h1 != null && h6 != null) {
    mom = clamp(50 + Math.min(h1, 40) * 1.2 + Math.min(h6, 60) * 0.4 - Math.max(0, h6 - 150) * 0.3);
    momWhy = `1h ${h1 >= 0 ? '+' : ''}${h1.toFixed(1)}%, 6h ${h6 >= 0 ? '+' : ''}${h6.toFixed(1)}%${h6 > 150 ? ' — overextended' : ''}`;
  }
  if (h24 != null && h24 <= -70) {
    mom = Math.min(mom ?? 100, 5);
    momWhy = `collapsed ${h24.toFixed(1)}% in 24h`;
  }
  f.push(['Momentum', 15, mom, momWhy]);
  const liq = n(pair?.liquidity?.usd); const mc = n(pair?.marketCap || pair?.fdv);
  const depth = liq && mc ? (liq / mc) * 100 : null;
  const depthScore = depth == null ? null : depth > 100 ? 15 : clamp(depth >= 10 ? 100 : depth >= 3 ? 55 + (depth - 3) * 6.4 : depth * 18);
  f.push(['Liquidity depth', 15, depthScore, depth == null ? 'liquidity not reported (bonding curve?)' : depth > 100 ? `${depth.toFixed(0)}% of market cap — abnormal, pool outlived the token` : `${depth.toFixed(1)}% of market cap`]);
  const t24 = (n(pair?.txns?.h24?.buys) || 0) + (n(pair?.txns?.h24?.sells) || 0);
  f.push(['Activity', 10, t24 ? clamp(Math.log10(t24) * 25) : null, t24 ? `${t24.toLocaleString()} trades in 24h` : 'no trade count']);
  if (rep && rep.score != null) f.push(['Creator trust', 20, rep.badge === 'flagged' ? 0 : rep.score, `${rep.badge} creator · ${rep.tokenCount} launches${rep.dumpedCount ? ` · ${rep.dumpedCount} dumped` : ''}`]);
  else f.push(['Creator trust', 20, null, 'creator not identified yet']);
  if (intel) {
    let v = 100; const why = [];
    if (intel.bundledWallets?.length >= 3) { v -= 30; why.push(`${intel.bundledWallets.length} bundled`); }
    if (intel.sniperWallets?.length >= 5) { v -= 20; why.push(`${intel.sniperWallets.length} snipers`); }
    if ((intel.insidersHoldingPct || 0) >= 10) { v -= 30; why.push(`insiders hold ${intel.insidersHoldingPct}%`); }
    if ((intel.top10Pct || 0) >= 35) { v -= 20; why.push(`top 10 hold ${intel.top10Pct}%`); }
    if ((intel.devHoldingPct || 0) >= 5) { v -= 20; why.push(`dev holds ${intel.devHoldingPct}%`); }
    f.push(['Launch forensics', 15, clamp(v), why.length ? why.join(' · ') : 'no bundle / sniper / concentration red flags']);
  } else f.push(['Launch forensics', 15, null, pair?.chainId === 'solana' ? 'reading chain…' : 'Solana only']);
  f.push(["Fee's read", 5, feeRead ? (feeRead.passes ? 100 : 40) : null, feeRead ? (feeRead.passes ? 'passes every entry rule' : `skip — ${feeRead.reason}`) : pair?.chainId === 'solana' ? 'checking…' : 'Solana only']);
  const scored = f.filter(x => x[2] != null);
  const weight = scored.reduce((a, x) => a + x[1], 0);
  let total = weight ? scored.reduce((a, x) => a + x[1] * x[2], 0) / weight : null;
  if (total != null && h24 != null && h24 <= -70) total = Math.min(total, 30);
  return { factors: f, total, coverage: weight / f.reduce((a, x) => a + x[1], 0) };
}

const grade = v => (v == null ? '—' : v >= 80 ? 'A' : v >= 65 ? 'B' : v >= 50 ? 'C' : v >= 35 ? 'D' : 'F');

export function EdgeScore({ pair }) {
  const rep = useReputation(pair);
  const intel = useIntel(pair);
  const feeRead = useFeeRead(pair);
  const { factors, total, coverage } = useMemo(() => computeEdge(pair, rep, intel, feeRead), [pair, rep, intel, feeRead]);
  const g = grade(total);
  return <section className="edge-score" data-testid="edge-score">
    <div className="edge-head">
      <div className={`edge-dial grade-${g}`} style={{ '--edge': `${total ?? 0}%` }}><i /><span><AnimatedNumber value={total == null ? 0 : Math.round(total)} format={v => String(Math.round(v))} /><small>EDGE</small></span></div>
      <div className="edge-title"><span className="eyebrow"><Gauge size={12} /> FEELESS EDGE SCORE</span><h3>Grade {g}</h3><p>One read from seven real signals. {Math.round(coverage * 100)}% of signals available — missing ones are excluded, never guessed. Not financial advice.</p></div>
    </div>
    <div className="edge-factors">{factors.map(([label, w, v, why]) => <div key={label} className={`edge-factor ${v == null ? 'is-na' : ''}`}>
      <div className="edge-factor-top"><b>{label}</b><small>{w}%</small><strong>{v == null ? 'n/a' : Math.round(v)}</strong></div>
      <div className="edge-bar"><i style={{ width: `${v ?? 0}%` }} className={v == null ? '' : v >= 65 ? 'good' : v >= 40 ? 'mid' : 'bad'} /></div>
      <small className="edge-why">{why}</small>
    </div>)}</div>
  </section>;
}
