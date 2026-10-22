import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { sharedJson } from '../lib/sharedJson';
import { resolveCoin } from '../lib/resolveCoin';
import { openWarRoom } from './WarRoomHost';
import { POOL_KIND, usd, apyTxt } from '../lib/cityPlan';
import '../styles/poolHub.css';

// 🏦 THE POOL HUB (the Pool Hall in Fee City + every pool building in the outer cities): every top and rising Solana pool in ONE pop-out —
// v2 AMMs, v3 / CLMM, DLMM bins, auto-compounding vaults, lending, liquid staking, perps, RWA — with live TVL, APY and its 7-day move.
// Each row does the real-money thing without "running to each site": ⚡ trade / stake through OUR engine (the war room's quick trade, your
// wallet signs), ＋ deposit on the pool's OWN page (opened exactly, your wallet signs there — FEELESS never holds funds), 🏠 set your
// family's building to it (display only). Data: /api/reputation/familia-pools (DefiLlama yields + our pair feed, ≤ 10 min old).
export const KIND_COLOR = { v2: '#ff9f45', v3: '#6ad7ff', dlmm: '#ffd36b', vault: '#3ddc84', lend: '#f5c451', stake: '#45e4c8', perps: '#ff5dbb', rwa: '#e8e3d6' };
const LENS = [['all', 'ALL'], ['v2', 'V2'], ['v3', 'V3'], ['dlmm', 'DLMM'], ['vault', 'VAULTS'], ['lend', 'LEND'], ['stake', 'STAKE'], ['perps', 'PERPS'], ['rwa', 'RWA']];
const SORT = [['tvl', 'TOP'], ['apy', 'YIELD'], ['rise', 'RISING']];

export function usePools() {
  const [v, setV] = useState(null);
  useEffect(() => { let on = true; const go = () => sharedJson('/api/reputation/familia-pools', { maxAge: 240000 }).then(d => on && d && setV(d)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 300000); return () => { on = false; clearInterval(t); }; }, []);
  return v;
}

// pure: the rows a lens + sort + search show
export function poolRows(pools, lens = 'all', sort = 'tvl', q = '') {
  const s = String(q || '').trim().toLowerCase();
  const rows = (pools || []).filter(r => (lens === 'all' || r.kind === lens) && (!s || `${r.sym} ${r.proto}`.toLowerCase().includes(s)));
  const key = { tvl: r => r.tvl || 0, apy: r => (r.apy == null ? -1 : r.apy), rise: r => r.rise || 0 }[sort] || (r => r.tvl || 0);
  return rows.slice().sort((a, b) => key(b) - key(a));
}
// pure: what the ⚡ button does for a row — trade the pool's token, stake into the LST, or nothing (lend / vault / RWA = deposit only)
export function tradeOf(r) {
  if (!r) return null;
  if (r.kind === 'stake') return r.hold ? { word: `Stake · buy ${r.sym}`, mint: r.hold } : null;
  if (['v2', 'v3', 'dlmm'].includes(r.kind)) return r.pair ? { word: `Trade ${r.sym.split('-')[0]}`, pair: r.pair } : r.hold ? { word: `Trade ${r.sym.split('-')[0]}`, mint: r.hold } : null;
  return null;
}

export async function goTrade(r) {
  const t = tradeOf(r); if (!t) return;
  if (t.pair) { openWarRoom({ chainId: 'solana', pairAddress: t.pair }); return; }
  const p = await resolveCoin('solana', t.mint);
  if (p?.pairAddress && !p.preMarket) openWarRoom({ chainId: 'solana', pairAddress: p.pairAddress }); else toast.error(`No pool to trade ${r.sym} through FEELESS yet — use ＋ Deposit on ${r.proto}.`);
}

function Gauge({ v }) {   // APY ring: fills to 50 % APY, gold past it
  const k = v == null ? 0 : Math.max(0.03, Math.min(1, v / 50));
  return <span className={`phb-gauge ${v != null && v >= 50 ? 'is-hot' : ''}`} style={{ '--k': k }} aria-hidden="true"><i /></span>;
}

// one pool, the same row in the hub list and the side panel
export function PoolRow({ r, i = 0, big = false, blocks = [], onLink }) {
  const [pick, setPick] = useState(false); const t = tradeOf(r);
  const tvlK = Math.max(0.04, Math.min(1, (Math.log10(1 + (r.tvl || 0)) - 4) / 5.5));
  return <li className={`phb-row k-${r.kind} ${big ? 'is-big' : ''}`} style={{ '--i': Math.min(i, 14), '--kc': KIND_COLOR[r.kind] || '#45e486' }} data-testid={`pool-${r.id}`}>
    <span className="phb-id"><b>{r.sym}</b><small>{r.proto} · {POOL_KIND[r.kind] || r.kind}{r.meta ? ` · ${r.meta}` : ''}</small></span>
    <span className="phb-tvl" data-tip={`Total value locked ${usd(r.tvl)}${r.vol ? ` · 24h volume ${usd(r.vol)}` : ''}`}><em>TVL</em><b className="m-num">{usd(r.tvl)}</b><u><s style={{ transform: `scaleX(${tvlK})` }} /></u></span>
    <span className="phb-apy" data-tip={r.apy == null ? 'No APY published for this DEX pool — its 24h volume vs liquidity shows how busy it is' : `APY ${apyTxt(r.apy)}${r.base != null ? ` · base ${apyTxt(r.base)}` : ''}${r.reward ? ` · rewards ${apyTxt(r.reward)}` : ''}${r.il ? ' · impermanent-loss risk' : ''}`}>
      <Gauge v={r.apy} /><span><em>{r.apy == null ? 'TURNOVER' : 'APY'}</em><b className="m-num">{r.apy == null ? `${Math.round(((r.vol || 0) / Math.max(1, r.tvl || 1)) * 100)}%` : apyTxt(r.apy)}</b></span></span>
    <span className={`phb-rise ${r.rise > 0 ? 'up' : r.rise < 0 ? 'dn' : ''}`} data-tip={r.d7 != null ? `APY move over 7 days: ${r.d7 >= 0 ? '+' : ''}${r.d7}` : 'How busy vs its size (24h volume ÷ liquidity)'}>{r.rise > 0 ? '▲' : r.rise < 0 ? '▼' : '•'} {Math.abs(r.rise || 0).toFixed(1)}</span>
    <span className="phb-acts">
      {t ? <button type="button" className="m-btn m-go" onClick={() => goTrade(r)} data-tip="Through FEELESS: the war room opens on this pool, you pick the amount, your wallet signs" data-testid={`pool-trade-${r.id}`}>⚡ {t.word}</button> : null}
      <a className="m-btn" href={r.app} target="_blank" rel="noopener noreferrer" data-tip={`${r.proto}'s own deposit page for this pool — your wallet signs there; FEELESS never holds your funds`} data-testid={`pool-deposit-${r.id}`}>＋ Deposit ↗</a>
      {onLink && blocks.length ? (pick ? <select className="m-input phb-pick" autoFocus defaultValue="" onChange={e => { if (e.target.value) { onLink(e.target.value, r); setPick(false); } }} onBlur={() => setPick(false)} aria-label="Which of your buildings">
        <option value="" disabled>Set which building…</option>{blocks.map(b => <option key={b} value={b}>{b}</option>)}</select>
        : <button type="button" className="m-btn" onClick={() => (blocks.length === 1 ? onLink(blocks[0], r) : setPick(true))} data-tip="Your family's building wears this pool: its name, kind and live APY on the billboard (display only)" data-testid={`pool-link-${r.id}`}>🏠 Set building</button>) : null}
    </span></li>;
}

export function PoolHub({ pools, blocks = [], onLink, start = 'all' }) {
  const [lens, setLens] = useState(start); const [sort, setSort] = useState('tvl'); const [q, setQ] = useState(''); const [qq, setQQ] = useState('');
  useEffect(() => { const t = setTimeout(() => setQQ(q), 250); return () => clearTimeout(t); }, [q]);
  const rows = useMemo(() => poolRows(pools?.pools, lens, sort, qq).slice(0, 60), [pools, lens, sort, qq]);
  const tvl = useMemo(() => (pools?.pools || []).reduce((a, r) => a + (r.tvl || 0), 0), [pools]);
  if (!pools) return <div className="phb phb-load" aria-live="polite"><i /><i /><i /><small>reading every pool…</small></div>;
  return <div className="phb" data-testid="pool-hub">
    <header className="phb-head"><span className="phb-big"><em>TRACKED TVL</em><b className="m-num" key={Math.round(tvl / 1e6)}>{usd(tvl)}</b></span>
      <span className="phb-kinds">{Object.entries(pools.kinds || {}).filter(([, n]) => n).map(([k, n]) => <i key={k} style={{ '--kc': KIND_COLOR[k] }} data-tip={`${n} ${POOL_KIND[k] || k} pools on Solana`}><b>{n}</b>{k.toUpperCase()}</i>)}</span></header>
    <div className="phb-ctl">
      <div className="m-seg phb-lens" role="tablist" aria-label="Pool kind">{LENS.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`phb-lens-${k}`}>{w}</button>)}</div>
      <div className="m-seg" role="tablist" aria-label="Sort">{SORT.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={sort === k} className={sort === k ? 'active' : ''} onClick={() => setSort(k)} data-testid={`phb-sort-${k}`}>{w}</button>)}</div>
      <input className="m-input phb-q" value={q} onChange={e => setQ(e.target.value)} placeholder="SOL, JitoSOL, USDC…" aria-label="Search pools" data-testid="phb-q" /></div>
    {rows.length ? <ol className="phb-list">{rows.map((r, i) => <PoolRow key={r.id} r={r} i={i} blocks={blocks} onLink={onLink} />)}</ol> : <p className="m-dim">No pool matches.</p>}
  </div>;
}
