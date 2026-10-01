import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';

// Fuse money side. FusePnl = a trader's own fuses (Trade › Fuse Lab). FuseHQ = Cmd Ctr: everyone's P&L, the paper
// arena (champions run a pretend $5 for 24h — the proof a strategy works), bloodlines, published-Fuse health.
const money = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0) >= 1e3 ? `${(Math.abs(v) / 1e3).toFixed(1)}K` : Math.abs(v || 0).toFixed(2)}`;
const pct = v => `${v >= 0 ? '+' : ''}${Math.abs(v) >= 1000 ? `${(1 + v / 100).toFixed(1)}x` : `${(v || 0).toFixed(1)}%`}`;
const tone = v => (v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');
const ago = t => { const s = Date.now() / 1000 - t; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

export function FusePnl() {
  const { wallet } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!addr) { setD(null); return undefined; }
    let alive = true; const load = () => fetch(apiUrl(`/api/reputation/fuses/pnl/${addr}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); window.addEventListener('feeless:fuse-pnl', load);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:fuse-pnl', load); };
  }, [addr]);
  if (!d?.positions) return null;
  return <section className="m-card fpn" data-testid="fuse-pnl">
    <div className="fpn-head"><span className="m-label">YOUR FUSES</span><b className={`m-num ${tone(d.pnlUsd)}`}>{money(d.pnlUsd)} <small>{pct(d.pnlPct)}</small></b><small className="m-dim">{money(d.valueUsd)} now · {d.positions} fused</small></div>
    <div className="fpn-rows">{d.rows.slice(0, 4).map(r => <div key={r.id} className="fpn-row"><span>{r.name}</span><small className="m-dim">{r.legs.map(l => l.symbol).join(' · ')} · {ago(r.at)}</small><b className={`m-num ${tone(r.pnlUsd)}`}>{pct(r.pnlPct)}</b></div>)}</div>
  </section>;
}

const TABS = [['pnl', '💰 P&L'], ['arena', '🏟 Arena'], ['blood', '🧬 Bloodline'], ['health', '🩺 Health']];

export function FuseHQ({ call }) {
  const [tab, setTab] = useState('pnl');
  const [d, setD] = useState(null); const [h, setH] = useState(null);
  const load = () => call('/admin/fuses/hq').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 60000); window.addEventListener('feeless:fuse-hq', load); return () => { clearInterval(t); window.removeEventListener('feeless:fuse-hq', load); }; }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (tab === 'health' && !h) call('/admin/fuses/health').then(setH).catch(e => toast.error(e.message)); }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps
  const b = d?.book;
  return <section className="m-card m-live fhq" data-testid="fuse-hq">
    <header className="fhq-head"><div><span className="m-label">⚛️ FUSE HQ</span><h4>What fusing actually makes.</h4></div>
      {b && <div className="fhq-total"><b className={`m-num ${tone(b.pnlUsd)}`}>{money(b.pnlUsd)}</b><small className="m-dim">{pct(b.pnlPct)} on {money(b.costUsd)} · {b.winners}▲ {b.losers}▼</small></div>}</header>
    <div className="m-seg" role="tablist">{TABS.map(([k, l]) => <button type="button" key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>
    {!d ? <div className="fl-row is-ghost" /> : <div className="fhq-body" key={tab}>
      {tab === 'pnl' && (b.positions ? <>
        <div className="fhq-grid">{b.fuses.map(f => <div key={f.fuseId} className="fhq-tile"><span>{f.name}</span><b className={`m-num ${tone(f.pnlUsd)}`}>{money(f.pnlUsd)}</b><small className="m-dim">{pct(f.pnlPct)} · {f.positions} fuses · {f.wallets} wallets</small></div>)}</div>
        <div className="fhq-list">{d.rows.slice(0, 12).map(r => <div key={r.id} className="fpn-row"><span>{r.name}</span><small className="m-dim"><a href={`/terminal/profile/${r.wallet}`}>{r.wallet.slice(0, 4)}…</a> · {r.legs.map(l => `${l.symbol} ${pct(l.pnlPct)}`).join(' · ')} · {ago(r.at)}</small><b className={`m-num ${tone(r.pnlUsd)}`}>{money(r.pnlUsd)}</b></div>)}</div>
      </> : <p className="m-dim">No real fuses yet. Every one-click Fuse in lands here with live P&L (only verified FEELESS buys count).</p>)}
      {tab === 'arena' && <>
        <p className="m-dim fhq-note">Champions run a pretend ${'5'} for 24h at real prices. A strategy is <b>proven</b> after {d.minSettled} settled runs with a positive average — traders' "Find my best 3" then uses it. Best now: <b className="m-pos">{d.bestStyle}</b>.</p>
        {d.board.length > 0 && <div className="fhq-grid">{d.board.map(r => <div key={r.style} className={`fhq-tile ${r.style === d.bestStyle ? 'is-best' : ''}`}><span>{r.style}</span><b className={`m-num ${tone(r.avgPct)}`}>{pct(r.avgPct)}</b><small className="m-dim">{r.runs} runs · {r.winRate}% win{r.beatsSol ? ' · beats SOL' : ''}</small></div>)}</div>}
        <div className="fhq-list">{d.arena.length ? d.arena.map(e => <div key={e.id} className="fpn-row"><span>{e.style}{e.settled ? ' ✓' : e.due ? ' · settling' : ''}</span><small className="m-dim">{e.legs.map(l => l.symbol).join(' · ')} · {ago(e.at)}</small><b className={`m-num ${tone(e.pnlPct)}`}>{pct(e.pnlPct)}</b></div>)
          : <p className="m-dim">Empty. In Evolution, hit 🏟 on a champion to enter it.</p>}</div>
      </>}
      {tab === 'blood' && <div className="fhq-list">{d.bloodline.length ? d.bloodline.map(x => <div key={x.pools.join()} className="fpn-row"><span>{x.style || '—'} · {x.fitness}</span><small className="m-dim">{x.symbols.join(' · ')} · {ago(x.at)}</small>
        <button type="button" className="m-btn fl-clear" onClick={() => call('/admin/fuses/hq', { method: 'POST', body: JSON.stringify({ action: 'unbloodline', pools: x.pools }) }).then(load).catch(e => toast.error(e.message))}>Drop</button></div>)
        : <p className="m-dim">Save champions with 🧬 in Evolution. Turn on "Breed from bloodline" and they seed the next run.</p>}</div>}
      {tab === 'health' && (!h ? <div className="fl-row is-ghost" /> : <div className="fhq-list">{h.fuses.length ? h.fuses.map(f => <div key={f.id} className="fpn-row"><span>{f.emoji} {f.name}</span>
        <small className="m-dim">{f.dead ? 'pools gone' : `fitness ${f.fitness} vs champion ${f.champion}`}</small><b className={f.dead || f.beaten ? 'm-neg' : 'm-pos'}>{f.dead ? 'DEAD' : f.beaten ? `BEATEN +${f.gapPct}%` : 'HEALTHY'}</b></div>)
        : <p className="m-dim">No published Fuses yet.</p>}</div>)}
    </div>}
  </section>;
}
