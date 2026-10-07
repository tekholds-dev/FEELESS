import '../../styles/fuseMoney.css';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { usd, txUrl } from '../FuseMoney';
import { CircleProfileForm, profileDraft } from '../CircleProfileEdit';
import '../../styles/fuseMoney.css';

// HQ › Fuse › 👛 Fuse wallet (owner only): the Circle wallet that funds FEELESS's tier cards with REAL money.
// 1 · pick the wallet + see its funds · 2 · hard limits · 3 · top up a tier (resets it as a new real run) or ↩ defund ·
// 4 · 🔍 dry run = real Jupiter quotes for what a top-up would buy (never signs) · 5 · the audit trail (every order + tx).
const ST = { filled: 'filled', done: 'done', dry: 'quoted', skipped: 'skipped', failed: 'failed', sent: 'sent' };
// Every limit in plain words (+ what it means for a $5 card). The card gets EXACTLY what you fund — fees come from the reserve.
const LIMITS = [['maxCardUsd', 'Biggest a card can get ($)', 'Fund + top-ups can never push one tier card above this. $10 = a $5 card can be topped up once more.'],
  ['maxSwapUsd', 'Biggest single swap ($)', 'One buy or sell is never bigger than this; a larger move is split over the next ticks.'],
  ['dailyUsd', 'All swaps per day ($)', 'Total of every swap in 24h. When it is reached the keeper waits until tomorrow.'],
  ['reserveSol', 'Fee reserve (SOL) — never goes into a card', 'Pays every swap\'s network fee (~$0.006) + the one-time account rent when the wallet first holds a coin (~$0.25). 0.015 SOL ≈ $1.80.'],
  ['slippageBps', 'Max slippage (bps · 100 = 1%)', 'A swap fails rather than fill worse than this. 200 = 2%.'],
  ['maxImpactPct', 'Max price impact (%)', 'A quote that would move the pool more than this is skipped.']];

/* 🔑 RPC keys (owner): which keeper lanes work, and ONE paste to add a key — tested before it is saved, live at once, never shown again. */
export function RpcKey({ call }) {
  const [d, setD] = useState(null);
  const [slot, setSlot] = useState(1);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const box = useRef(null);
  const load = useCallback(() => call('/admin/rpc').then(x => { setD(x); return x; }).catch(() => setD({ lanes: [], error: true })), [call]);
  useEffect(() => { load().then(x => { const ask = new URLSearchParams(window.location.search).get('rpc');
    if (x && (x.needsKey || ask)) { const free = (x.slots || []).find(q => !q.set); const dead = (x.lanes || []).find(l => l.spent && l.slot);
      setSlot(free ? free.slot : dead ? dead.slot : 1); if (ask && box.current) { box.current.open = true; box.current.querySelector('input')?.focus(); } } });
    const t = setInterval(() => !document.hidden && load(), 60000); return () => clearInterval(t); }, [load]);
  if (!d || d.error) return null;
  const lanes = d.lanes || [];
  const save = async e => { e.preventDefault(); if (!url.trim()) return; setBusy(true); setMsg(null);
    try { const r = await call('/admin/rpc', { method: 'POST', body: JSON.stringify({ slot, url: url.trim() }) });
      setUrl(''); setMsg({ ok: true, text: `✓ Lane ${r.slot} is live on ${r.provider} (${r.ms} ms${r.holders ? ' · holder scans OK' : ' · no holder scans on this plan'}). Saved — nothing to restart for real swaps.` });
      toast.success('RPC key saved and live'); await load(); }
    catch (er) { setMsg({ ok: false, text: er.message || 'Not saved' }); } finally { setBusy(false); } };
  return <details ref={box} className={`hrt-fold rpck ${d.needsKey ? 'is-need' : ''}`} data-testid="rpc-key" open={d.needsKey || undefined}>
    <summary><b>🔑 RPC keys</b><span>{!lanes.length ? 'no key set — real swaps use slower public nodes' : lanes.map(l => `${l.provider} ${l.spent ? `out of quota · back in ${l.backInMin >= 90 ? `${Math.round(l.backInMin / 60)}h` : `${l.backInMin}m`}` : 'ok'}`).join(' · ')}</span>
      {d.needsKey && <i className="rpck-need" data-testid="rpc-need">ADD A KEY</i>}</summary>
    <div className="rpck-body">
      <ul className="rpck-lanes">{lanes.map(l => <li key={l.lane} className={l.spent ? 'is-spent' : 'is-ok'} data-tip={l.spent ? 'This plan is used up — the keeper skips it until it resets' : 'In quota — the keeper uses it'}><b>LANE {l.lane}</b><span>{l.provider}</span><em>{l.spent ? `out · ${l.backInMin}m` : '● ok'}</em></li>)}</ul>
      <form className="rpck-form" onSubmit={save}>
        <div className="m-seg" role="group" aria-label="Which lane">{((d.slots || []).length ? d.slots.map(q => q.slot) : [1, 2]).map(n => <button key={n} type="button" className={slot === n ? 'on' : ''} disabled={busy} data-testid={`rpc-slot-${n}`} data-tip={n === 1 ? 'The keeper asks this one first' : `Backup ${n - 1}: used the moment the lanes before it are busy or out of quota`} onClick={() => setSlot(n)}>{n}{(d.slots || []).find(q => q.slot === n)?.set ? ' ●' : ''}</button>)}</div>
        <input className="m-input" type="password" autoComplete="off" spellCheck={false} placeholder="Paste the https:// RPC URL from Helius / QuickNode" value={url} disabled={busy} data-testid="rpc-url" aria-label="RPC URL" onChange={e => setUrl(e.target.value)} />
        <button type="submit" className="m-btn m-go" disabled={busy || !url.trim()} data-testid="rpc-save">{busy ? 'Testing…' : 'Test & save'}</button></form>
      {msg && <small className={`m-note ${msg.ok ? '' : 'warn'}`} data-testid="rpc-msg">{msg.text}</small>}
      <small className="m-dim">The URL is tested first (it must answer), saved on this machine only, and never shown again. Other services pick it up at their next restart.</small></div></details>;
}

export function FuseWallet({ call }) {
  const [d, setD] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [amt, setAmt] = useState({});
  const [dry, setDry] = useState(null);
  const [showStuck, setShowStuck] = useState(false);
  const load = useCallback(() => call('/admin/fuse-wallet').then(x => { setD(x); setCfg(c => c || x.cfg); }).catch(e => setD({ error: e.message })), [call]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => clearInterval(t); }, [load]);
  const save = patch => call('/admin/fuse-wallet/cfg', { method: 'POST', body: JSON.stringify(patch) }).then(x => { setCfg(x.cfg); toast.success('Fuse wallet saved'); load(); }).catch(e => toast.error(e.message));
  const topup = tpl => { const v = Number(amt[tpl]); if (!(v >= 1)) { toast.error('Enter at least $1'); return; }
    call('/admin/fuse-wallet/topup', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(x => { toast.success(x.first ? `💵 ${d.tiers[tpl]} funded with $${v} — new real run` : `💵 +$${v} — new run`); load(); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)); };
  const preview = tpl => { const v = Number(amt[tpl]) || 20; setDry({ tpl, busy: true });
    call('/admin/fuse-wallet/preview', { method: 'POST', body: JSON.stringify({ tpl, usd: v }) }).then(x => setDry({ tpl, usd: v, ...x })).catch(e => { setDry(null); toast.error(e.message); }); };
  const cardAct = (tpl, action) => call('/admin/fuse-wallet/card', { method: 'POST', body: JSON.stringify({ tpl, action }) }).then(() => { toast.success(action === 'defund' ? '↩ Selling every coin back to SOL' : action === 'halt' ? '⏸ Card halted' : '▶ Resumed'); load(); }).catch(e => toast.error(e.message));
  const recoverSell = r => {
    if (!window.confirm(`Force sell old ${r.symbol} still held by the Fuse wallet and return the confirmed SOL to ${d.tiers?.[r.card] || r.card} card cash?`)) return;
    call('/admin/fuse-wallet/recover-sell', { method: 'POST', body: JSON.stringify({ tpl: r.card, mint: r.mint }) })
      .then(() => { toast.success(`🧹 ${r.symbol} recovered — force sell running; proceeds stay in card cash`); load(); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => toast.error(e.message));
  };
  if (!d) return <section className="m-card fw"><span className="loader" /> Loading the Fuse wallet…</section>;
  const sol = d.balances?.sol;
  const tokens = Object.values(d.balances?.tokens || {}).filter(v => Number(v) > 0).length;
  const cardSol = Object.values(d.books || {}).reduce((sum, b) => sum + Number(b.sol || 0) + Number(b.bankSol || 0), 0);
  const reserveSol = Number(d.cfg?.reserveSol || 0);
  const freeSol = Number(d.freeSol || 0);
  const allocationGap = sol == null ? null : sol - cardSol - reserveSol - freeSol;
  const story = d.solProvenance?.depositedSol > 0 ? d.solProvenance : null;
  // ➜ one tap: your unassigned SOL into the real card (or the first tier), never past the per-card cap
  const sweepTpl = Object.keys(d.books || {})[0];
  const sweepRoom = sweepTpl ? Math.max(0, Number(d.cfg?.maxCardUsd || 0) - Number(d.books[sweepTpl].valueUsd || 0)) : 0;
  const sweepUsd = Math.floor(Math.min(freeSol * Number(d.solUsd || 0), sweepRoom) * 100) / 100;
  const sweep = sweepTpl && sweepUsd >= 1 ? { tpl: sweepTpl, usd: sweepUsd, label: d.tiers?.[sweepTpl] || sweepTpl } : null;
  return <section className="m-card m-live fw" data-testid="fuse-wallet">
    <header className="m-row"><span className="m-label">👛 FUSE WALLET · REAL MONEY FOR TIER CARDS</span><small className="m-dim">owner only · every change audited</small></header>
    {!d.signer && <div className="fw-lock" data-testid="fw-lock"><b>🔒 Signing is not enabled yet.</b> Everything here works except sending: pick the wallet, see its funds, set limits and run 🔍 dry runs with real Jupiter quotes.
      Turning on signing (Circle signs each swap the keeper builds) is docs/GO_LIVE.md step 2 — it needs your go-ahead. Until then tier cards stay paper at true fills.</div>}
    {d.error && <small className="m-note warn">{d.error}</small>}
    <RpcKey call={call} />
    <div className="fw-kpis">
      <span><small>SOL IN WALLET</small><b className="m-num">{sol != null ? sol.toFixed(4) : '—'}</b><em>{sol != null ? usd(sol * d.solUsd) : 'pick a wallet'}</em></span>
      <span data-tip="SOL not currently assigned to a card or the fee reserve. It may include your deposits and returned token-account rent; it is not automatically card profit."><small>UNASSIGNED SOL</small><b className="m-num">{d.freeSol != null ? d.freeSol.toFixed(4) : '—'}</b><em>{d.freeSol != null ? usd(d.freeSol * d.solUsd) : ''}</em></span>
      <span><small>COINS HELD</small><b className="m-num">{tokens}</b><em>{Object.keys(d.books || {}).length} funded cards</em></span>
      <span data-tip="Real fills vs the paper model — paper uses this so its entries match real money"><small>PAPER CALIBRATION</small><b className="m-num">×{d.calibration?.impactMult ?? 1}</b><em>{d.calibration?.n ? `${d.calibration.spreadPct ? `+${d.calibration.spreadPct}% per swap · ` : ''}from ${d.calibration.n} real fills` : 'needs 3 real fills'}</em></span>
      <span data-tip="Paper fills vs real Jupiter quotes for the same coins and $ (every ~5 min, read-only)"><small>PAPER ⇄ REAL QUOTES</small><b className="m-num">{d.paperMatch?.n ? `${d.paperMatch.avgDevPct >= 0 ? '+' : ''}${d.paperMatch.avgDevPct}%` : '—'}</b><em>{d.paperMatch?.n ? `${d.paperMatch.within2Pct}% within 2% · ${d.paperMatch.n} checks` : 'first check in ~5 min'}</em></span>
      <span><small>SWAPS · FEES</small><b className="m-num">{d.totals?.swaps || 0}</b><em>network {usd(d.totals?.feesUsd)}</em></span></div>
    {sol != null && <div className="m-note" data-testid="fw-sol-breakdown"><b>Wallet SOL is fully separated:</b><span>{sol.toFixed(4)} total = {cardSol.toFixed(4)} card cash + {reserveSol.toFixed(4)} fee reserve + {freeSol.toFixed(4)} unassigned.</span>
      {story ? <span data-testid="fw-story">💰 Chain audit: you deposited <b className="m-num">{story.depositedSol.toFixed(4)} SOL</b> ({usd(story.depositedSol * d.solUsd)}) in {story.n} transfer{story.n === 1 ? '' : 's'} → {(story.cardSol + story.coinsSol).toFixed(4)} in cards (SOL + coins) · {story.reserveSol.toFixed(4)} fee reserve · <b className="m-num">{story.unassignedSol.toFixed(4)} unassigned</b> · {story.spentSol.toFixed(4)} spent (trading result + network fees + open coin accounts). Unassigned is YOUR deposited SOL that no card was ever given — not profit, not fees.</span>
        : <span>Unassigned is not proven profit or a new deposit. Audit: {Number(d.solProvenance?.cardFundedSol || 0).toFixed(4)} SOL funded into cards; {Number(d.solProvenance?.rentReturnedSol || 0).toFixed(4)} SOL cumulatively returned from closed token accounts.</span>}
      {story?.deposits?.length > 0 && <small className="m-dim">{story.deposits.map(r => <a key={r.sig} className="fw-dep" href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noreferrer" data-tip={`from ${r.from}`}>{new Date(r.at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} +{Number(r.sol).toFixed(4)} ↗ </a>)}</small>}
      {sweep && <button type="button" className="m-btn" data-testid="fw-sweep" data-tip={`Fills the top-up box for ${sweep.label} with ${usd(sweep.usd)} of your unassigned SOL (kept inside the ${usd(d.cfg?.maxCardUsd)} per-card cap). You still press Top up — it counts as new money PUT IN.`} onClick={() => setAmt(a => ({ ...a, [sweep.tpl]: sweep.usd.toFixed(2) }))}>➜ Put {usd(sweep.usd)} unassigned into {sweep.label}</button>}
      {Math.abs(allocationGap) > 0.000001 && <small className="m-dim">Refresh timing difference: {allocationGap.toFixed(6)} SOL. No balance is assigned or spent until a confirmed transaction updates the book.</small>}
      {d.balances?.stale && <small className="m-dim">Showing the last confirmed balance because the live RPC read is temporarily unavailable.</small>}</div>}
    {d.missing?.length > 0 && <div className="m-note warn" data-testid="fw-missing"><b>⚠ Coins missing from the wallet</b><span>{d.missing.map(m => `${m.mint.slice(0, 6)}… booked ${m.booked}, held ${m.held}`).join(' · ')} — halt the card and check the audit trail.</span></div>}
    {d.recoverable?.length > 0 && <div className="m-note warn" data-testid="fw-recoverable"><span className="m-row">
      <button type="button" className="m-btn danger" onClick={() => setShowStuck(v => !v)} data-testid="fw-stuck-toggle">
        🧹 Failed / stuck balances ({d.recoverable.length})
      </button>
      <small className="m-dim">Old keeper coins still physically in the Fuse wallet.</small>
    </span>
      {showStuck && <div className="fw-tiers" data-testid="fw-stuck-panel">
        {d.recoverable.map(r => <div key={r.mint} className="fw-tier">
          <span><b>${r.symbol}</b><small className="m-dim"> · {d.tiers?.[r.card] || r.card} · {r.lastStatus || 'old keeper balance'}{r.lastErr ? ` · ${r.lastErr}` : ''}</small>
            <small className="m-dim">Sell converts the confirmed wallet balance back to SOL and keeps it inside this card as cash. Card value / P&L update from the confirmed fill.</small></span>
          <button type="button" className="m-btn danger" onClick={() => recoverSell(r)}
            data-testid={`fw-recover-${r.symbol}`} data-tip="Sell this old keeper balance back into its original card cash">Sell → card cash</button>
        </div>)}
      </div>}
    </div>}
    <div className="m-row"><span className="m-label">1 · WALLET</span>
      <select className="m-input" value={cfg?.walletId || ''} onChange={e => { const w = d.wallets.find(x => x.id === e.target.value); save({ walletId: w?.id || '', address: w?.address || '' }); }} data-testid="fw-pick">
        <option value="">Pick a Circle Solana wallet…</option>{(d.wallets || []).map(w => <option key={w.id} value={w.id}>{w.name || 'wallet'} · {w.address.slice(0, 4)}…{w.address.slice(-4)} · {w.blockchain}</option>)}</select>
      {cfg?.address && <a className="m-btn" href={`https://solscan.io/account/${cfg.address}`} target="_blank" rel="noreferrer">Solscan ↗</a>}
      <small className="m-dim">fund it by sending SOL to its address (HQ › Money › Circle can move SOL between your wallets)</small></div>
    {/* arm / kill stay in sight; the six hard limits fold away behind their own one-line summary */}
      <div className="m-row"><label className="m-toggle" data-tip="A rotation normally sells the old coin, then buys the new one (two transactions). ON: when ONE route from the old coin straight into the new one delivers at least as many coins and its impact is ≤ 4%, the keeper sends one transaction instead — one fee, no moment in cash, all or nothing. It is decided from three read-only quotes before anything moves; otherwise it does the two swaps as before."><input type="checkbox" checked={!!cfg?.coinToCoin} onChange={e => save({ coinToCoin: e.target.checked })} data-testid="fw-c2c" /><span>{cfg?.coinToCoin ? '🔀 One-transaction swaps ON' : '🔀 One-transaction swaps off'}</span></label></div>
      <div className="m-row"><label className="m-toggle" data-tip={d.signer ? 'Armed = the keeper may swap for funded cards' : 'Needs signing enabled first'}><input type="checkbox" checked={!!cfg?.armed} disabled={!d.signer} onChange={e => save({ armed: e.target.checked })} data-testid="fw-armed" /><span>{cfg?.armed ? '🟢 Armed' : 'Not armed'}</span></label>
        <label className="m-toggle"><input type="checkbox" checked={!!cfg?.paused} onChange={e => save({ paused: e.target.checked })} data-testid="fw-paused" /><span>{cfg?.paused ? '⏸ Paused (nothing trades)' : 'Kill switch off'}</span></label></div>
    <details className="hrt-fold" data-testid="fw-limits"><summary><b>2 · Hard limits</b><span>card ≤ ${cfg?.maxCardUsd} · swap ≤ ${cfg?.maxSwapUsd} · day ${cfg?.dailyUsd} · fee reserve {cfg?.reserveSol} SOL · slippage {((cfg?.slippageBps || 0) / 100).toFixed(1)}% · impact {cfg?.maxImpactPct}% — server-enforced; what you fund is what the card gets</span></summary>
<div className="fw-grid">{LIMITS.map(([k, l, tip]) => <label key={k}>{l}
      <input className="m-input m-num" type="number" defaultValue={cfg?.[k]} onBlur={e => Number(e.target.value) !== cfg?.[k] && save({ [k]: Number(e.target.value) })} data-testid={`fw-${k}`} /><small className="m-dim">{tip}</small></label>)}</div></details>
    <div><span className="m-label">3 · TIER CARDS · TOP UP = NEW RUN</span><div className="fw-tiers">{Object.entries(d.tiers || {}).map(([tpl, label]) => { const b = d.books?.[tpl];
      return <div key={tpl} className={`fw-tier ${b ? 'is-real' : ''}`} data-testid={`fw-tier-${tpl}`}><span><b>{label}</b><small className="m-dim">{b ? ` · 💵 ${usd(b.valueUsd)} now · funded ${usd(b.fundedUsd)} · ${b.swaps} swaps${b.halt ? ' · ⏸ halted' : ''}${b.defund ? ' · ↩ selling' : ''}` : ' · 📄 paper'}</small>
        {b && <small className="m-dim" data-testid={`fw-receipt-${tpl}`}>🧾 receipt: in {usd(b.topups || b.fundedUsd)} → bought {usd(b.bought)} · sold {usd(b.sold)} · network fees {usd(b.feesUsd)} · now {usd(b.valueUsd)} ({b.fundedUsd ? `${((b.valueUsd / b.fundedUsd - 1) * 100).toFixed(1)}%` : '—'})</small>}</span>
        <input className="m-input m-num" inputMode="decimal" placeholder="$" value={amt[tpl] || ''} onChange={e => setAmt(a => ({ ...a, [tpl]: e.target.value.replace(/[^0-9.]/g, '') }))} aria-label={`${label} top-up $`} data-testid={`fw-amt-${tpl}`} />
        <button type="button" className="m-btn" onClick={() => preview(tpl)} data-tip="Real Jupiter quotes for what this $ would buy now — never signs" data-testid={`fw-dry-${tpl}`}>🔍 Dry run</button>
        <span className="m-row"><button type="button" className="m-btn primary m-go" disabled={!d.signer || !cfg?.armed} onClick={() => topup(tpl)} data-testid={`fw-topup-${tpl}`}>💵 {b ? 'Top up' : 'Fund'}</button>
          {b && <><button type="button" className="m-btn" onClick={() => cardAct(tpl, b.halt ? 'resume' : 'halt')}>{b.halt ? '▶' : '⏸'}</button><button type="button" className="m-btn danger" onClick={() => cardAct(tpl, 'defund')} data-tip="Sell every coin back to SOL; the card returns to paper">↩</button></>}</span></div>; })}</div></div>
    {dry && <div className="ff-detail" data-testid="fw-dryrun"><b>🔍 Dry run · {d.tiers[dry.tpl]} · {usd(dry.usd)}</b>{dry.busy ? <small className="m-dim">quoting…</small> : <>
      {dry.card && <><span data-testid="fw-dry-status">📄 Paper now: {usd(dry.card.paperUsd)} ({dry.card.paperPct >= 0 ? '+' : ''}{dry.card.paperPct}%) · round {dry.card.rounds + 1}{dry.card.phase ? ` · ${dry.card.phase} phase` : ''}</span>
        <div className="ctab" role="table"><div className="ctab-row is-head" role="row"><span>COIN</span><span>WEIGHT</span><span>YOUR $</span><span>SINCE ENTRY</span></div>
          {dry.card.coins.map(c => <div key={c.pairAddress} className="ctab-row" role="row"><b>{c.role === 'anchor' ? '⚓ ' : c.role === 'runner' ? '🏃 ' : ''}${c.symbol}{c.frozen ? ' ❄' : ''}</b><span className="m-num">{c.weightPct}%</span>
            <span className="m-num">{usd(c.usd)}</span><em className={`m-num ${c.pricePct >= 0 ? 'm-pos' : 'm-neg'}`}>{c.pricePct >= 0 ? '+' : ''}{c.pricePct}%</em></div>)}</div>
        <small className="m-dim">{dry.note}</small></>}
      {(dry.orders || []).map((o, i) => <span key={i}>{o.side === 'buy' ? '🟢 buy' : '🔴 sell'} ${o.symbol} · {usd(o.usd)}{o.err ? ` · ⚠ ${o.err}` : ` · impact ${o.impactPct}% · via ${(o.route || []).join(' → ') || 'Jupiter'}`}</span>)}
      {!dry.orders?.length && <small className="m-dim">No swaps needed — this card is SOL right now (its SOL slice stays SOL).</small>}
      <b data-testid="fw-dry-fees">💳 Card gets {usd(dry.cardUsd)} · fees ≈ {usd(dry.feesUsdEst)} from the reserve (network {usd(dry.networkUsdEst)}{dry.newCoins ? ` + account rent for ${dry.newCoins} new coin${dry.newCoins > 1 ? 's' : ''} ${usd(dry.rentUsdEst)}, refunded into the card` : ''}) · FEELESS fee $0</b></>}</div>}
    <RunReport call={call} />
    {/* every row is kept — the trail just opens on demand instead of pushing the page four screens down */}
    <details className="hrt-fold" data-testid="fw-audit"><summary><b>4 · Audit trail</b><span>{d.ledger?.length || 0} rows · bought {usd(d.totals?.bought)} · sold {usd(d.totals?.sold)} · top-ups {usd(d.totals?.topups)}{d.ledger?.[0] ? ` · last: ${d.ledger[0].side} ${d.ledger[0].symbol ? `$${d.ledger[0].symbol} ` : ''}${new Date(d.ledger[0].at * 1000).toLocaleTimeString()}` : ''}</span></summary>
      <div className="fw-table" role="table" data-testid="fw-ledger"><div className="fw-row is-head" role="row"><span>WHEN</span><span>CARD</span><span>WHAT</span><span>$</span><span>FILL</span><span>FEE</span><span>TX</span></div>
        {(d.ledger || []).map((o, i) => <div key={i} className="fw-row" role="row"><span className="m-dim">{new Date(o.at * 1000).toLocaleTimeString()}</span><span>{o.card}</span>
          <span>{o.side} {o.symbol ? `$${o.symbol}` : ''} <em className={`fw-st s-${o.status}`}>{ST[o.status] || o.status}</em>{o.err ? <small className="m-dim"> · {o.err}</small> : null}</span>
          <span className="m-num">{usd(o.usd)}</span><span className="m-num">{o.px ? `$${Number(o.px).toPrecision(4)}` : o.impactPct != null ? `${o.impactPct}% imp` : '—'}</span><span className="m-num">{o.feeUsd != null ? usd(o.feeUsd) : '—'}</span>
          {o.sig ? <a href={txUrl(o.sig)} target="_blank" rel="noreferrer">tx ↗</a> : <span className="m-dim">—</span>}</div>)}
        {!d.ledger?.length && <small className="m-dim">No orders yet — top-ups and every keeper swap land here (dry runs are shown above, never stored).</small>}</div></details>
  </section>;
}

// 🩺 Real run report: what each real card ACTUALLY did (audit ledger only) and the flaws it shows, each with the setting that fixes it.
export function RunReport({ call }) {
  const [r, setR] = useState(null);
  useEffect(() => { call('/admin/fuse-wallet/report').then(setR).catch(e => setR({ error: e.message })); }, [call]);
  const reps = r?.reports || [];
  const bad = reps.reduce((n, x) => n + (x.flaws || []).length, 0);
  return <details className="hrt-fold fw-report" open={bad > 0} data-testid="fw-report"><summary><b>🩺 Real run report</b>
    <span>{!r ? 'reading the ledger…' : r.error ? r.error : !reps.length ? 'no real runs yet' : `${reps.length} card${reps.length > 1 ? 's' : ''} · ${bad} flaw${bad === 1 ? '' : 's'} found`}</span></summary>
    {reps.map(x => <article key={x.card} className={`fw-rep v-${x.verdict}`} data-testid={`fw-rep-${x.card}`}>
      <header><b>{x.label}</b><em className={`fw-verdict v-${x.verdict}`}>{x.verdict === 'clean' ? '✅ clean' : x.verdict === 'fix' ? '🛠 fix' : '👀 watch'}</em>{!x.open && <small className="m-dim">closed</small>}</header>
      <dl className="m-kv"><dt>Ran</dt><dd>{x.hours}h · {x.swaps} swaps ({x.perHour}/h)</dd><dt>Money in → now</dt><dd>{usd(x.fundedUsd)} → {x.equityUsd != null ? usd(x.equityUsd) : '—'}{x.pnlPct != null ? ` (${x.pnlPct >= 0 ? '+' : ''}${x.pnlPct}%)` : ''}{x.holdSolPct != null ? ` · SOL held ${x.holdSolPct >= 0 ? '+' : ''}${x.holdSolPct}%` : ''}</dd>
        <dt>Network fees</dt><dd>{usd(x.feesUsd)} · {x.feesPct}% of money in</dd><dt>Round trips</dt><dd>{x.trips} (lost {usd(x.tripLossUsd)})</dd>
        <dt>Fill vs market</dt><dd>{x.slipPct != null ? `${x.slipPct}%` : '—'}</dd><dt>Failed / skipped</dt><dd>{x.failed}{x.failPct != null ? ` (${x.failPct}%)` : ''} / {x.skipped}</dd></dl>
      {(x.flaws || []).map((f, i) => <p key={i} className={`m-note fw-flaw l-${f.level}`}><b>{f.level === 'high' ? '🔴' : '🟡'} {f.what}</b><span>Fix: {f.fix}</span></p>)}
      {x.skipWhy?.length > 0 && <small className="m-dim">Blocked by: {x.skipWhy.map(w => `${w.why} ×${w.n}`).join(' · ')}</small>}
      {x.coins?.length > 0 && <small className="m-dim">Per coin (sold − bought): {x.coins.slice(0, 8).map(c => `$${c.symbol} ${c.netUsd >= 0 ? '+' : ''}${c.netUsd.toFixed(2)}`).join(' · ')}</small>}
    </article>)}
  </details>;
}

// 🪪 Circle wallet profiles (owner): search your Circle wallets and edit each one's public FEELESS profile from the creator wallet.
export function CircleProfiles({ call }) {
  const [d, setD] = useState(null);
  const [q, setQ] = useState('');
  const [edit, setEdit] = useState(null);
  const load = useCallback(() => call('/admin/circle/profiles').then(setD).catch(e => setD({ wallets: [], error: e.message })), [call]);
  useEffect(() => { load(); }, [load]);
  const rows = (d?.wallets || []).filter(w => !q || `${w.name} ${w.address} ${w.profile?.handle || ''} ${w.profile?.name || ''}`.toLowerCase().includes(q.toLowerCase()));
  return <section className="m-card fw" data-testid="circle-profiles"><span className="m-label">🪪 CIRCLE WALLET PROFILES · SEARCH + EDIT</span>
    <input className="m-input" placeholder="Search name, @handle or address" value={q} onChange={e => setQ(e.target.value)} data-testid="cp-search" />
    {d?.error && <small className="m-note warn">{d.error}</small>}
    <div className="fw-tiers">{rows.map(w => <div key={w.id} className="fw-tier"><span><b>{w.profile?.name || w.name}</b><small className="m-dim"> {w.profile?.handle ? `@${w.profile.handle} · ` : ''}{w.address.slice(0, 4)}…{w.address.slice(-4)} · {w.blockchain}</small></span>
      <a className="m-btn" href={`/terminal/profile/${w.address}`} target="_blank" rel="noreferrer">Profile ↗</a>
      <button type="button" className="m-btn" onClick={() => setEdit(profileDraft(w))} data-testid={`cp-edit-${w.id}`}>✏️ Edit</button></div>)}</div>
    {edit && <CircleProfileForm call={call} start={edit} onDone={saved => { setEdit(null); if (saved) load(); }} />}
  </section>;
}
