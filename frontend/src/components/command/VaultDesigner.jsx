import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../../lib/api';
import { useSolPrice } from '../../lib/solPrice';
import '../../styles/fusePage.css';

// Command Center › ⚛️ Fuse › 🏦 FUSE Vault designer. One vault = up to 3 SOLANA yield pools (v2 constant-product / v3
// concentrated) in one contract: SOL in → shares → spread by auto-scaled weights, capped per pool, fees to the vault fee
// wallet (Trading & fees). Status stays DESIGN until the on-chain program is audited and deployed — nothing here moves funds.
// Every number is shown in SOL AND $ (live SOL price) so the money is readable at a glance.
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : v >= 10 ? `$${Math.round(v || 0)}` : `$${(v || 0).toFixed(2)}`);
const sol = v => `${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 3 })} SOL`;
const EMPTY = { name: '', emoji: '🏦', tagline: '', mgmtBps: 100, perfBps: 1000, pools: [] };
// 🏦 Prebuilt vaults: one tap fills the designer (real Solana pools looked up live, then you tweak + save). Pool fee APRs are
// estimates; caps stop the vault owning more than cap% of any pool.
export const VAULT_PRESETS = [
  { id: 'stable', emoji: '🏛', name: 'Huge Stable', tier: 'ever', why: 'Deepest SOL / USDC, JitoSOL and BTC pools — calm fees, tiny swings', q: ['SOL USDC', 'JitoSOL', 'cbBTC'], mgmtBps: 50, perfBps: 1000, capPct: 1, rangePct: 10 },
  { id: 'blue', emoji: '⚖', name: 'Blue-chip Blend', tier: 'gold', why: 'SOL, ETH and JUP — majors that trade all day', q: ['SOL USDC', 'WETH', 'JUP'], mgmtBps: 100, perfBps: 1000, capPct: 1.5, rangePct: 15 },
  { id: 'pump', emoji: '🌊', name: 'Pump Economy', tier: 'blaze', why: 'PUMP, BONK and WIF — the meme economy\'s deepest pools', q: ['PUMP', 'BONK', 'WIF'], mgmtBps: 100, perfBps: 1500, capPct: 2, rangePct: 25 },
  { id: 'degen', emoji: '🔥', name: 'Degen Yield', tier: 'next', why: 'The 3 highest-fee deep pools right now (live) — biggest yield, biggest swings', lens: 'yield', mgmtBps: 150, perfBps: 2000, capPct: 2, rangePct: 30 },
];
const APR_CAP = 400;
const STEPS = [['① Deposit', 'A holder sends SOL and gets vault SHARES (their slice of everything inside).'],
  ['② Spread', 'The contract splits it over ≤3 Solana pools — weights follow each pool\'s fee APR + depth (10–70% each), never more than the cap % of a pool.'],
  ['③ Earn', 'Those pools pay trading fees to liquidity → the share price grows. Price moves of the coins also move it (both ways).'],
  ['④ Withdraw', 'Shares → SOL any time, even when paused. FEELESS keeps the mgmt %/yr + performance % of the YIELD only, to the vault fee wallet.']];

export function VaultDesigner({ call }) {
  const [d, setD] = useState(null); const [deposit, setDeposit] = useState(10);
  const [draft, setDraft] = useState(EMPTY); const [q, setQ] = useState(''); const [found, setFound] = useState([]);
  const px = useSolPrice();
  const $ = s => (px ? usd(Number(s || 0) * px) : '—');
  const dep = Number(deposit) > 0 ? Number(deposit) : 10;
  const load = () => call(`/admin/vaults?deposit=${dep}`).then(setD).catch(e => toast.error(e.message));
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [deposit]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (q.trim().length < 2) { setFound([]); return undefined; }
    const t = setTimeout(() => fetch(apiUrl(`/api/reputation/vaults/pools?q=${encodeURIComponent(q.trim())}`)).then(r => r.json()).then(x => setFound(x.pools || [])).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [q]);
  const add = p => { setQ(''); setFound([]); setDraft(x => (x.pools.some(l => l.pairAddress === p.pairAddress) || x.pools.length >= 3 ? x
    : { ...x, pools: [...x.pools, { pairAddress: p.pairAddress, chainId: 'solana', symbol: `${p.symbol}/${p.quote}`, kind: p.kind, venue: p.venue, weight: 1, capPct: 2, rangePct: p.kind === 'v3' ? 20 : null, meta: p }] })); };
  const setPool = (i, patch) => setDraft(x => ({ ...x, pools: x.pools.map((p, j) => (j === i ? { ...p, ...patch } : p)) }));
  // 🏟 Vault ← Arena: a Prime card's majors + pools become the vault's pools (runners stay on cards — a vault earns pool fees,
  // so it needs deep pools). Each coin's deepest Solana pool is looked up live; max 3.
  const [arena, setArena] = useState([]);
  useEffect(() => { fetch(apiUrl('/api/reputation/fuses/prime')).then(r => r.json()).then(x => setArena(x.cards || [])).catch(() => {}); }, []);
  const fromCard = async c => {
    const legs = c.legs.filter(l => l.role !== 'runner').slice(0, 3);
    const hits = await Promise.all(legs.map(l => fetch(apiUrl(`/api/reputation/vaults/pools?q=${encodeURIComponent(l.mint)}`)).then(r => r.json()).then(x => (x.pools || []).find(p => p.pairAddress === l.pairAddress) || (x.pools || [])[0]).catch(() => null)));
    const got = hits.filter(Boolean);
    if (!got.length) { toast.error('No vault-ready pools on that card right now.'); return; }
    setDraft(x => ({ ...x, name: x.name || `${c.label.replace(/^\S+\s/, '')} Vault`, emoji: '🏟', pools: [] }));
    got.forEach(add); toast.success(`${got.length} pools from ${c.label} loaded — set weights + caps, then save`);
  };
  const loadPreset = async v => {
    const pick = v.lens
      ? ((await fetch(apiUrl(`/api/reputation/fuses/discover?lens=${v.lens}`)).then(r => r.json()).catch(() => ({}))).pools || []).filter(p => (p.liquidityUsd || 0) >= 200000).slice(0, 3)
        .map(p => fetch(apiUrl(`/api/reputation/vaults/pools?q=${encodeURIComponent(p.baseAddress || p.pairAddress)}`)).then(r => r.json()).then(x => (x.pools || []).find(y => y.pairAddress === p.pairAddress) || (x.pools || [])[0]).catch(() => null))
      : v.q.map(q => fetch(apiUrl(`/api/reputation/vaults/pools?q=${encodeURIComponent(q)}`)).then(r => r.json()).then(x => (x.pools || [])[0]).catch(() => null));
    const got = (await Promise.all(pick)).filter(Boolean);
    if (!got.length) { toast.error('Pools unavailable right now — try again in a minute.'); return; }
    setDraft({ ...EMPTY, name: `${v.name} Vault`, emoji: v.emoji, tagline: v.why, mgmtBps: v.mgmtBps, perfBps: v.perfBps, pools: [] });
    got.forEach(add);
    setDraft(x => ({ ...x, pools: x.pools.map(p => ({ ...p, capPct: v.capPct, rangePct: p.kind === 'v3' ? v.rangePct : null })) }));
    toast.success(`${v.emoji} ${v.name} loaded — ${got.length} pools · check the split below, then save`);
  };
  const save = async body => { try { await call('/admin/vaults', { method: 'POST', body: JSON.stringify(body) }); toast.success('Vault saved'); setDraft(EMPTY); load(); } catch (e) { toast.error(e.message); } };
  // Draft money preview: weighted pool APR (capped like the engine) on the simulated deposit → yield and what each fee takes.
  const wsum = draft.pools.reduce((a, p) => a + (Number(p.weight) || 0), 0) || 1;
  const apr = draft.pools.reduce((a, p) => a + Math.min(APR_CAP, Number(p.meta?.aprEst) || 0) * (Number(p.weight) || 0) / wsum, 0);
  const yieldSol = dep * apr / 100; const mgmtSol = dep * draft.mgmtBps / 10000; const perfSol = yieldSol * draft.perfBps / 10000;
  return <div className="vd" data-testid="vault-designer">
    <div className="m-note warn vd-status"><b>🏦 DESIGN · LOCALNET ONLY · NOT DEPLOYED</b><span>No money can go in yet. Fees would go to {d?.feeWallet ? <code>{d.feeWallet.slice(0, 4)}…{d.feeWallet.slice(-4)}</code> : 'the vault fee wallet (set it in Trading & fees)'}. Deploy = adapters → devnet → audit → your keys.</span></div>
    <ol className="vd-flow">{STEPS.map(([t, why], i) => <li key={t} style={{ '--i': i }} data-tip={why}><b>{t}</b><small>{why}</small></li>)}</ol>

    <section className="vd-pre" aria-label="Prebuilt vaults">{VAULT_PRESETS.map((v, i) => <button key={v.id} type="button" className={`vd-pcard tier-${v.tier}`} style={{ '--i': i }} onClick={() => loadPreset(v)} data-testid={`vd-preset-${v.id}`}
      data-tip={`${v.why}. Fees: ${v.mgmtBps / 100}%/yr + ${v.perfBps / 100}% of yield · cap ${v.capPct}% of each pool${v.rangePct ? ` · v3 range ±${v.rangePct}%` : ''}`}>
      <i className="vd-pcrest">{v.emoji}</i><b>{v.name}</b><small>{v.why}</small><em>{v.mgmtBps / 100}%/yr · {v.perfBps / 100}% of yield</em><span className="vd-pgo">Load →</span></button>)}</section>
    <section className="m-card vd-sim-box"><div className="m-row"><span className="m-label">🧮 SIMULATE A DEPOSIT</span>
      <label className="vd-dep"><input className="m-input" inputMode="decimal" value={deposit} onChange={e => setDeposit(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="Deposit in SOL" /><span>SOL</span><em className="m-dim">{$(dep)}</em></label></div>
      {!(d?.vaults || []).length ? <p className="m-dim">No vault designed yet — build one below and its money math shows here.</p>
        : (d.vaults).map(v => <article key={v.id} className="vd-vault">
          <header className="m-row"><span className="fz-emoji">{v.emoji}</span><b>{v.name}</b><span className="m-chip">{v.status}</span>
            <small className="m-dim">{v.mgmtBps / 100}%/yr mgmt · {v.perfBps / 100}% of yield</small><span className="vd-sp" />
            <button type="button" className="m-btn" onClick={() => setDraft({ id: v.id, name: v.name, emoji: v.emoji, tagline: v.tagline || '', mgmtBps: v.mgmtBps, perfBps: v.perfBps, pools: v.pools.map(p => ({ ...p, meta: p })) })}>Edit</button>
            <button type="button" className="m-btn danger" onClick={() => window.confirm(`Delete ${v.name}?`) && save({ id: v.id, delete: true })}>Delete</button></header>
          <div className="vd-kpis">
            <span data-tip="Weighted fee APR of the pools at their live weights (capped at 400%)"><small>BLENDED APR</small><b className="m-num">{v.sim.blendedAprPct}%</b></span>
            <span data-tip={`What ${sol(dep)} would earn in pool fees over a year (before price moves)`}><small>YIELD / YEAR</small><b className="m-num m-pos">{$(v.sim.yearlyYieldSol)}</b><em>{sol(v.sim.yearlyYieldSol)} · {$(v.sim.yearlyYieldSol / 365)}/day</em></span>
            <span data-tip="Mgmt %/yr + performance % of the yield — paid to the vault fee wallet"><small>FEELESS KEEPS / YR</small><b className="m-num">{$(v.sim.yearlyFeeSol)}</b><em>{sol(v.sim.yearlyFeeSol)}</em></span>
            <span data-tip="Most SOL the vault takes before a pool's cap is hit — more than this waits in the buffer"><small>CAPACITY</small><b className="m-num">{$(v.sim.capacitySol)}</b><em>{sol(v.sim.capacitySol)}</em></span>
            <span data-tip="SOL that didn't fit under the caps — kept as SOL, not forced into a pool"><small>BUFFER</small><b className="m-num">{$(v.sim.bufferSol)}</b><em>{sol(v.sim.bufferSol)}</em></span></div>
          <div className="vd-pools">{v.pools.map(p => <div key={p.pairAddress} className="vd-pool">
            <b>{p.symbol}</b><span className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`} data-tip={p.kind === 'v3' ? `Concentrated: earns only while price stays within ±${p.rangePct}%` : 'Constant product: always in range, lower fee share'}>{p.kind}{p.kind === 'v3' ? ` ±${p.rangePct}%` : ''}</span>
            <small className="m-dim">{p.venue} · {usd(p.liquidityUsd)} deep · {p.aprEst ?? '—'}% APR · cap {p.capPct}%</small>
            <i className="vd-bar"><i style={{ transform: `scaleX(${Math.max(0.02, p.liveWeight || 0)})` }} /></i>
            <em className="m-num">{Math.round((p.liveWeight || 0) * 100)}% → {$(v.sim.allocation[p.pairAddress])}</em></div>)}</div>
        </article>)}</section>

    <section className="m-card vd-build"><div className="m-row"><span className="m-label">{draft.id ? '✎ EDIT VAULT' : '＋ DESIGN A VAULT'}</span><small className="m-dim">Solana pools only · max 3 · saved as a design</small></div>
      {arena.length > 0 && <div className="vd-arena"><small className="m-label">🏟 START FROM AN ARENA CARD</small><div className="m-row">{arena.map(c => <button key={c.id} type="button" className="vd-hit" onClick={() => fromCard(c)} data-testid={`vd-from-${c.tpl}`}
        data-tip={`Loads ${c.legs.filter(l => l.role !== 'runner').map(l => l.symbol).join(' · ') || 'its pools'} as vault pools — the vault earns their trading fees`}><b>{c.label}</b><small>{c.legs.filter(l => l.role !== 'runner').map(l => `$${l.symbol}`).join(' · ')} · {c.pnlPct >= 0 ? '+' : ''}{c.pnlPct.toFixed(1)}%</small></button>)}</div></div>}
      <div className="vd-step"><span className="vd-n">1</span><div className="vd-fields"><input className="m-input fz-emoji-in" value={draft.emoji} onChange={e => setDraft({ ...draft, emoji: e.target.value })} aria-label="Emoji" />
        <input className="m-input" placeholder="Vault name (e.g. FEE Yield)" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} aria-label="Vault name" /></div></div>
      <div className="vd-step"><span className="vd-n">2</span><div className="vd-fields">
        <label className="m-field" data-tip={`Charged on the whole deposit per year. On ${sol(dep)}: ${$(mgmtSol)}/yr`}><span>Mgmt %/yr (≤{(d?.maxMgmtBps || 300) / 100})</span><input className="m-input" type="number" step="0.1" min="0" value={draft.mgmtBps / 100} onChange={e => setDraft({ ...draft, mgmtBps: Math.round(Number(e.target.value) * 100) })} /></label>
        <label className="m-field" data-tip="Share of the YIELD only — no yield, no performance fee"><span>Performance % of yield (≤{(d?.maxPerfBps || 3000) / 100})</span><input className="m-input" type="number" min="0" value={draft.perfBps / 100} onChange={e => setDraft({ ...draft, perfBps: Math.round(Number(e.target.value) * 100) })} /></label>
        <p className="vd-money" data-testid="vd-money">On <b>{sol(dep)}</b> ({$(dep)}){draft.pools.length ? <> at ≈ <b>{apr.toFixed(0)}% APR</b>: holder earns <b className="m-pos">{$(yieldSol - perfSol - mgmtSol)}/yr</b>, FEELESS keeps <b>{$(mgmtSol + perfSol)}/yr</b> ({$(mgmtSol)} mgmt + {$(perfSol)} performance).</> : <> — add pools to see the split.</>}</p></div></div>
      <div className="vd-step"><span className="vd-n">3</span><div className="vd-fields vd-col">
        {draft.pools.map((p, i) => <div key={p.pairAddress} className="vd-leg"><b>{p.symbol}</b><span className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`}>{p.kind}</span><small className="m-dim">{p.meta ? `${usd(p.meta.liquidityUsd)} deep · ${p.meta.aprEst}% APR` : ''}</small>
          <label className="m-field" data-tip="Starting share vs the other pools; live weights then follow APR + depth"><span>Weight</span><input className="m-input" type="number" min="1" value={p.weight} onChange={e => setPool(i, { weight: Number(e.target.value) })} /></label>
          <label className="m-field" data-tip="Never own more than this % of the pool (the vault must not BE the market)"><span>Cap % of pool</span><input className="m-input" type="number" step="0.1" min="0.1" max="10" value={p.capPct} onChange={e => setPool(i, { capPct: Number(e.target.value) })} /></label>
          {p.kind === 'v3' && <label className="m-field" data-tip="Narrow = more fees while in range, zero fees when price leaves it"><span>Range ±%</span><input className="m-input" type="number" min="2" max="100" value={p.rangePct} onChange={e => setPool(i, { rangePct: Number(e.target.value) })} /></label>}
          <button type="button" className="m-btn danger" onClick={() => setDraft({ ...draft, pools: draft.pools.filter((_, j) => j !== i) })} aria-label="Remove pool">✕</button></div>)}
        {draft.pools.length < 3 && <input className="m-input" placeholder="Search Solana pools — SOL, USDC, FEE, BTC…" value={q} onChange={e => setQ(e.target.value)} aria-label="Search pools" data-testid="vault-search" />}
        {found.length > 0 && draft.pools.length < 3 && <div className="vd-found">{found.map(p => <button type="button" key={p.pairAddress} className="vd-hit" onClick={() => add(p)}>
          <b>{p.symbol}/{p.quote}</b>{p.real && <i className="fl-real" data-tip="The real coin's mint">✓ REAL</i>}{p.impostor && <i className="fl-fake" data-tip="Same ticker as a major, different mint">⚠ lookalike</i>}
          <em className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`}>{p.kind}</em><small>{p.venue} · {usd(p.liquidityUsd)} deep · {usd(p.volume24h)} vol · {p.aprEst}% APR</small></button>)}</div>}</div></div>
      <div className="m-row"><button type="button" className="m-btn primary m-go" disabled={!draft.name || !draft.pools.length} onClick={() => save({ ...draft, pools: draft.pools.map(({ meta, ...p }) => p) })}>{draft.id ? 'Save vault' : 'Save vault design'}</button>
        {draft.id && <button type="button" className="m-btn" onClick={() => setDraft(EMPTY)}>Cancel</button>}</div></section>
  </div>;
}
