import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { usd, txUrl } from '../FuseMoney';
import '../../styles/fuseMoney.css';

// HQ › Fuse › 👛 Fuse wallet (owner only): the Circle wallet that funds FEELESS's tier cards with REAL money.
// 1 · pick the wallet + see its funds · 2 · hard limits · 3 · top up a tier (resets it as a new real run) or ↩ defund ·
// 4 · 🔍 dry run = real Jupiter quotes for what a top-up would buy (never signs) · 5 · the audit trail (every order + tx).
const ST = { filled: 'filled', done: 'done', dry: 'quoted', skipped: 'skipped', failed: 'failed', sent: 'sent' };
const LIMITS = [['maxCardUsd', 'Max per card ($)', 'A tier card never holds more than this'], ['maxSwapUsd', 'Max per swap ($)', 'Bigger moves split over ticks'],
  ['dailyUsd', 'Daily cap ($)', 'All swaps in 24h'], ['reserveSol', 'Keep for network fees (SOL)', 'Never spent on cards'],
  ['slippageBps', 'Slippage (bps)', '100 = 1%, max 300'], ['maxImpactPct', 'Max price impact (%)', 'A quote over this is skipped']];

export function FuseWallet({ call }) {
  const [d, setD] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [amt, setAmt] = useState({});
  const [dry, setDry] = useState(null);
  const load = useCallback(() => call('/admin/fuse-wallet').then(x => { setD(x); setCfg(c => c || x.cfg); }).catch(e => setD({ error: e.message })), [call]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => clearInterval(t); }, [load]);
  const save = patch => call('/admin/fuse-wallet/cfg', { method: 'POST', body: JSON.stringify(patch) }).then(x => { setCfg(x.cfg); toast.success('Fuse wallet saved'); load(); }).catch(e => toast.error(e.message));
  const topup = tpl => { const v = Number(amt[tpl]); if (!(v >= 1)) { toast.error('Enter at least $1'); return; }
    call('/admin/fuse-wallet/topup', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(x => { toast.success(x.first ? `💵 ${d.tiers[tpl]} funded with $${v} — new real run` : `💵 +$${v} — new run`); load(); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)); };
  const preview = tpl => { const v = Number(amt[tpl]) || 20; setDry({ tpl, busy: true });
    call('/admin/fuse-wallet/preview', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(x => setDry({ tpl, usd: v, ...x })).catch(e => { setDry(null); toast.error(e.message); }); };
  const cardAct = (tpl, action) => call('/admin/fuse-wallet/card', { method: 'POST', body: JSON.stringify({ tpl, action }) }).then(() => { toast.success(action === 'defund' ? '↩ Selling every coin back to SOL' : action === 'halt' ? '⏸ Card halted' : '▶ Resumed'); load(); }).catch(e => toast.error(e.message));
  if (!d) return <section className="m-card fw"><span className="loader" /> Loading the Fuse wallet…</section>;
  const sol = d.balances?.sol; const tokens = Object.keys(d.balances?.tokens || {}).length;
  return <section className="m-card m-live fw" data-testid="fuse-wallet">
    <header className="m-row"><span className="m-label">👛 FUSE WALLET · REAL MONEY FOR TIER CARDS</span><small className="m-dim">owner only · every change audited</small></header>
    {!d.signer && <div className="fw-lock" data-testid="fw-lock"><b>🔒 Signing is not enabled yet.</b> Everything here works except sending: pick the wallet, see its funds, set limits and run 🔍 dry runs with real Jupiter quotes.
      Turning on signing (Circle signs each swap the keeper builds) is docs/GO_LIVE.md step 2 — it needs your go-ahead. Until then tier cards stay paper at true fills.</div>}
    {d.error && <small className="m-note warn">{d.error}</small>}
    <div className="fw-kpis">
      <span><small>SOL IN WALLET</small><b className="m-num">{sol != null ? sol.toFixed(4) : '—'}</b><em>{sol != null ? usd(sol * d.solUsd) : 'pick a wallet'}</em></span>
      <span data-tip="SOL not owned by a card and not kept back for network fees — what top-ups can use"><small>FREE FOR TOP-UPS</small><b className="m-num">{d.freeSol != null ? d.freeSol.toFixed(4) : '—'}</b><em>{d.freeSol != null ? usd(d.freeSol * d.solUsd) : ''}</em></span>
      <span><small>COINS HELD</small><b className="m-num">{tokens}</b><em>{Object.keys(d.books || {}).length} funded cards</em></span>
      <span data-tip="Real fills vs the paper model — paper uses this so its entries match real money"><small>PAPER CALIBRATION</small><b className="m-num">×{d.calibration?.impactMult ?? 1}</b><em>{d.calibration?.n ? `from ${d.calibration.n} real fills` : 'needs 3 real fills'}</em></span>
      <span><small>SWAPS · FEES</small><b className="m-num">{d.totals?.swaps || 0}</b><em>network {usd(d.totals?.feesUsd)}</em></span></div>
    {d.missing?.length > 0 && <div className="m-note warn" data-testid="fw-missing"><b>⚠ Coins missing from the wallet</b><span>{d.missing.map(m => `${m.mint.slice(0, 6)}… booked ${m.booked}, held ${m.held}`).join(' · ')} — halt the card and check the audit trail.</span></div>}
    <div className="m-row"><span className="m-label">1 · WALLET</span>
      <select className="m-input" value={cfg?.walletId || ''} onChange={e => { const w = d.wallets.find(x => x.id === e.target.value); save({ walletId: w?.id || '', address: w?.address || '' }); }} data-testid="fw-pick">
        <option value="">Pick a Circle Solana wallet…</option>{(d.wallets || []).map(w => <option key={w.id} value={w.id}>{w.name || 'wallet'} · {w.address.slice(0, 4)}…{w.address.slice(-4)} · {w.blockchain}</option>)}</select>
      {cfg?.address && <a className="m-btn" href={`https://solscan.io/account/${cfg.address}`} target="_blank" rel="noreferrer">Solscan ↗</a>}
      <small className="m-dim">fund it by sending SOL to its address (HQ › Money › Circle can move SOL between your wallets)</small></div>
    <div><span className="m-label">2 · HARD LIMITS (server-enforced)</span><div className="fw-grid">{LIMITS.map(([k, l, tip]) => <label key={k} data-tip={tip}>{l}
      <input className="m-input m-num" type="number" defaultValue={cfg?.[k]} onBlur={e => Number(e.target.value) !== cfg?.[k] && save({ [k]: Number(e.target.value) })} data-testid={`fw-${k}`} /></label>)}</div>
      <div className="m-row"><label className="m-toggle" data-tip={d.signer ? 'Armed = the keeper may swap for funded cards' : 'Needs signing enabled first'}><input type="checkbox" checked={!!cfg?.armed} disabled={!d.signer} onChange={e => save({ armed: e.target.checked })} data-testid="fw-armed" /><span>{cfg?.armed ? '🟢 Armed' : 'Not armed'}</span></label>
        <label className="m-toggle"><input type="checkbox" checked={!!cfg?.paused} onChange={e => save({ paused: e.target.checked })} data-testid="fw-paused" /><span>{cfg?.paused ? '⏸ Paused (nothing trades)' : 'Kill switch off'}</span></label></div></div>
    <div><span className="m-label">3 · TIER CARDS · TOP UP = NEW RUN</span><div className="fw-tiers">{Object.entries(d.tiers || {}).map(([tpl, label]) => { const b = d.books?.[tpl];
      return <div key={tpl} className={`fw-tier ${b ? 'is-real' : ''}`} data-testid={`fw-tier-${tpl}`}><span><b>{label}</b><small className="m-dim">{b ? ` · 💵 ${usd(b.valueUsd)} now · funded ${usd(b.fundedUsd)} · ${b.swaps} swaps${b.halt ? ' · ⏸ halted' : ''}${b.defund ? ' · ↩ selling' : ''}` : ' · 📄 paper'}</small></span>
        <input className="m-input m-num" inputMode="decimal" placeholder="$" value={amt[tpl] || ''} onChange={e => setAmt(a => ({ ...a, [tpl]: e.target.value.replace(/[^0-9.]/g, '') }))} aria-label={`${label} top-up $`} data-testid={`fw-amt-${tpl}`} />
        <button type="button" className="m-btn" onClick={() => preview(tpl)} data-tip="Real Jupiter quotes for what this $ would buy now — never signs" data-testid={`fw-dry-${tpl}`}>🔍 Dry run</button>
        <span className="m-row"><button type="button" className="m-btn primary m-go" disabled={!d.signer || !cfg?.armed} onClick={() => topup(tpl)} data-testid={`fw-topup-${tpl}`}>💵 {b ? 'Top up' : 'Fund'}</button>
          {b && <><button type="button" className="m-btn" onClick={() => cardAct(tpl, b.halt ? 'resume' : 'halt')}>{b.halt ? '▶' : '⏸'}</button><button type="button" className="m-btn danger" onClick={() => cardAct(tpl, 'defund')} data-tip="Sell every coin back to SOL; the card returns to paper">↩</button></>}</span></div>; })}</div></div>
    {dry && <div className="ff-detail" data-testid="fw-dryrun"><b>🔍 Dry run · {d.tiers[dry.tpl]} · {usd(dry.usd)}</b>{dry.busy ? <small className="m-dim">quoting…</small> : <>
      {(dry.orders || []).map((o, i) => <span key={i}>{o.side === 'buy' ? '🟢 buy' : '🔴 sell'} ${o.symbol} · {usd(o.usd)}{o.err ? ` · ⚠ ${o.err}` : ` · impact ${o.impactPct}% · via ${(o.route || []).join(' → ') || 'Jupiter'}`}</span>)}
      {!dry.orders?.length && <small className="m-dim">Nothing to buy — the card's coins are SOL only.</small>}<small className="m-dim">network ≈ {usd(dry.networkUsdEst)} · FEELESS fee $0 (HQ cards)</small></>}</div>}
    <div><span className="m-label">4 · AUDIT TRAIL · {d.ledger?.length || 0} ROWS · BOUGHT {usd(d.totals?.bought)} · SOLD {usd(d.totals?.sold)} · TOP-UPS {usd(d.totals?.topups)}</span>
      <div className="fw-table" role="table" data-testid="fw-ledger"><div className="fw-row is-head" role="row"><span>WHEN</span><span>CARD</span><span>WHAT</span><span>$</span><span>FILL</span><span>FEE</span><span>TX</span></div>
        {(d.ledger || []).map((o, i) => <div key={i} className="fw-row" role="row"><span className="m-dim">{new Date(o.at * 1000).toLocaleTimeString()}</span><span>{o.card}</span>
          <span>{o.side} {o.symbol ? `$${o.symbol}` : ''} <em className={`fw-st s-${o.status}`}>{ST[o.status] || o.status}</em>{o.err ? <small className="m-dim"> · {o.err}</small> : null}</span>
          <span className="m-num">{usd(o.usd)}</span><span className="m-num">{o.px ? `$${Number(o.px).toPrecision(4)}` : o.impactPct != null ? `${o.impactPct}% imp` : '—'}</span><span className="m-num">{o.feeUsd != null ? usd(o.feeUsd) : '—'}</span>
          {o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer">tx ↗</a> : <span className="m-dim">—</span>}</div>)}
        {!d.ledger?.length && <small className="m-dim">No orders yet — top-ups and every keeper swap land here (dry runs are shown above, never stored).</small>}</div></div>
  </section>;
}
