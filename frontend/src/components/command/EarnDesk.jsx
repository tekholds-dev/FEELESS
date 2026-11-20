import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ExternalLink, Copy, Check } from 'lucide-react';
import '../../styles/earnDesk.css';

// 💼 Slice 16 (owner 2026-11-19: "poeco can do upwork and other stuff … no face … whatever pays real money!!"). PoEco earns:
// the board = the best faceless listings from PUBLIC feeds, scored on fit / pay / deadline / the minds' cost, with expected profit.
// A filing = both minds' blind bids (the stronger kept) moving through the approve door. FEELESS never sends, delivers or holds money:
// an approve hands the owner the bid to send from HIS OWN account; he marks what happened; it is graded on what the platform paid him.
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v) >= 10 ? Math.abs(v).toFixed(0) : Math.abs(v).toFixed(2)}`);
const PLAT = { superteam: 'Superteam', freelancer: 'Freelancer', algora: 'Algora' };
const TRACK = [['bid', 'Bid drafted'], ['bid_approved', 'You approved'], ['sent', 'You sent it'], ['won', 'Won'], ['work', 'Work done'], ['checked', 'Collective checked'], ['delivery_approved', 'You approved delivery'], ['paid', 'Paid']];
const PARTS = [['fit', 'FIT', 30], ['pay', 'PAY', 30], ['deadline', 'TIME', 20], ['profit', 'PROFIT', 20]];

function Meter({ label, v, max, tip }) {
  return <span className="ern-m" data-tip={tip}><small>{label}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, (v || 0) / max))})` }} /></i><b className="m-num">{Math.round(v || 0)}</b></span>;
}

function Listing({ r, i, busy, onBid }) {
  return <motion.li className="ern-row" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 8) * 0.04 }} data-testid={`ern-row-${i}`}>
    <span className="ern-score m-num" data-tip="Fit 30 + pay 30 + time 20 + profit 20">{r.score}</span>
    <div className="ern-main"><a href={r.url} target="_blank" rel="noopener noreferrer" className="ern-title">{r.title}<ExternalLink size={11} aria-hidden="true" /></a>
      <span className="ern-facts"><em className="m-chip">{PLAT[r.src] || r.src}</em><em className="m-chip ok">{r.cat}</em><span>{r.pay}</span><span>{r.daysLeft == null ? 'no deadline' : `${r.daysLeft} d left`}</span><span>{r.rivals} entered</span></span>
      <span className="ern-meters">{PARTS.map(([k, l, m]) => <Meter key={k} label={l} v={r.parts?.[k]} max={m} />)}</span></div>
    <div className="ern-side"><b className={`m-num ${(r.expProfit || 0) > 0 ? 'is-up' : ''}`} data-tip={`${Math.round((r.chance || 0) * 100)}% win chance × ${usd(r.payUsd)} − minds ${usd(r.cost)}`}>{usd(r.expProfit)}</b><small>EXPECTED</small>
      <button type="button" className="m-btn" disabled={busy} onClick={() => onBid(r.id)} data-tip="Both minds draft the bid blind. Nothing is sent" data-testid={`ern-bid-${i}`}>Draft bid</button></div>
  </motion.li>;
}

export function EarnBoard({ v, busy, onFind, onBid }) {
  const b = v?.board || {}; const best = b.best || []; const kept = (v?.platforms || []).filter(p => p.in); const out = (v?.platforms || []).filter(p => !p.in);
  const top = best[0];
  return <section className="ern m-card" data-testid="ern-board">
    <header className="ern-h"><h4>💼 EARN REAL MONEY · FACELESS WORK</h4><button type="button" className="m-btn m-go" disabled={busy} onClick={onFind} data-tip="Reads every kept platform's public feed. No login" data-testid="ern-find">{busy ? 'Working…' : best.length ? 'Read the feeds again' : 'Find paid work'}</button></header>
    {best.length ? <p className="ern-verdict" data-testid="ern-verdict"><b>{top.title}</b> pays best for the minds: <span className="m-num">{usd(top.expProfit)}</span> expected after <span className="m-num">{usd(top.cost)}</span> of minds. {b.kept} open listings fit, from {b.seen} read.</p>
      : <p className="ern-say">{b.at ? 'No open faceless listing fits right now.' : 'It reads Superteam Earn, Freelancer.com and Algora bounties (public feeds only), keeps the faceless work its minds can do, and shows the best with the expected profit.'}</p>}
    {best.length ? <ol className="ern-list">{best.map((r, i) => <Listing key={r.id} r={r} i={i} busy={busy} onBid={onBid} />)}</ol> : null}
    {b.out?.length ? <p className="ern-out" data-testid="ern-out"><small>LEFT OUT</small>{b.out.slice(0, 3).map(o => <span key={o.why}><b className="m-num">{o.n}</b> {o.why}</span>)}</p> : null}
    <details className="ern-terms" data-testid="ern-terms"><summary>Terms first: {kept.length} platforms kept, {out.length} out</summary>
      <ul>{kept.map(p => <li key={p.id} className="is-in"><b>{p.name}</b> {p.terms} <i>{p.how}</i></li>)}{out.map(p => <li key={p.id}><b>{p.name}</b> out: {p.why}</li>)}</ul></details>
  </section>;
}

function Bid({ b, kept }) {
  return <article className={`ern-bid${kept ? ' is-kept' : ''}`} data-testid={`ern-bid-mind-${b.mind}`}><header><b>Mind {'AB'[b.mind % 2]}</b><em>{kept ? 'KEPT' : 'NOT KEPT'}</em><span className="m-num">{b.score}</span></header>
    {b.bid ? <p className="ern-text">{b.bid}</p> : <p className="ern-say">No readable bid came back.</p>}
    {b.plan?.length ? <ol className="ern-plan">{b.plan.map((s, i) => <li key={i}>{s}</li>)}</ol> : null}
    <small className="ern-why">{(b.why || []).join(' · ')}</small></article>;
}

export function EarnFiling({ f, onBack, busy, act }) {
  const [real, setReal] = useState(false); const [why, setWhy] = useState(''); const [amt, setAmt] = useState(''); const [fee, setFee] = useState(''); const [cur, setCur] = useState('USD'); const [copied, setCopied] = useState(false);
  const l = f.listing || {}; const at = TRACK.findIndex(([k]) => k === f.stage); const ended = f.stage === 'lost' || f.stage === 'unpaid'; const test = !!(f.test || f.testRun);
  const go = (stage, extra = {}) => act({ op: 'earn_go', job: f.id, tools: { stage, ...extra } });
  const copy = async () => { try { await navigator.clipboard.writeText(f.bid?.bid || ''); setCopied(true); } catch { setCopied(false); } };
  const g = f.graded;
  return <div className="ern-f" data-testid={`ern-f-${f.id}`}>
    <header className="eco-bh"><button type="button" className="m-btn" onClick={onBack} data-testid="eco-back">← PoEco</button><b>PoEco #{f.n} · earn</b>{test ? <em className="trec-tag">TEST</em> : null}</header>
    <a className="ern-ft" href={l.url} target="_blank" rel="noopener noreferrer" data-testid="ern-listing">{l.title}<ExternalLink size={12} aria-hidden="true" /></a>
    <span className="ern-facts"><em className="m-chip">{f.platform?.name}</em><em className="m-chip ok">{l.cat}</em><span>{l.pay}</span><span>{l.daysLeft == null ? 'no deadline' : `${l.daysLeft} d left`}</span><span>{l.rivals} entered</span><span>score <b className="m-num">{l.score}</b></span></span>
    <div className="ern-kpis"><span><small>EXPECTED PROFIT</small><b className="m-num is-up">{usd(l.expProfit)}</b></span><span><small>MINDS COST</small><b className="m-num">{usd(f.cost)}</b></span><span><small>HOURS SAVED</small><b className="m-num">{l.hours}</b></span><span><small>WIN CHANCE</small><b className="m-num">{Math.round((l.chance || 0) * 100)}%</b></span></div>
    <ol className="ern-track" aria-label="Where it stands" data-testid="ern-track">{TRACK.map(([k, lab], i) => <li key={k} className={ended ? (i <= Math.max(0, at) ? 'is-done' : '') : i < at ? 'is-done' : i === at ? 'is-now' : ''}>{lab}</li>)}{ended ? <li className="is-bad">{f.stage === 'lost' ? 'Lost' : 'Unpaid'}</li> : null}</ol>
    <div className="ern-bids">{(f.bids || []).map(b => <Bid key={b.mind} b={b} kept={b.mind === f.kept} />)}</div>
    <section className="ern-door m-card" data-testid="ern-door">
      {f.stage === 'bid' ? <><p className="ern-say">Nothing has been sent. Approve the kept bid, then send it yourself from your own {f.platform?.name} account. {f.platform?.how}</p>
        {test ? <label className="ern-tick"><input type="checkbox" checked={real} onChange={e => setReal(e.target.checked)} data-testid="ern-real" /> This test is real: I mean to send it</label> : null}
        <button type="button" className="m-btn m-go" disabled={busy || (test && !real)} onClick={() => go('bid_approved', { real })} data-testid="ern-approve">Approve the bid</button></> : null}
      {f.stage === 'bid_approved' ? <><p className="ern-say">Approved. Copy it, send it from your own account, then mark it sent.</p><span className="ern-acts"><button type="button" className="m-btn" onClick={copy} data-testid="ern-copy">{copied ? <Check size={13} /> : <Copy size={13} />} Copy the bid</button>
        <a className="m-btn" href={l.url} target="_blank" rel="noopener noreferrer">Open the listing <ExternalLink size={12} /></a><button type="button" className="m-btn m-go" disabled={busy} onClick={() => go('sent')} data-testid="ern-sent">I sent it</button></span></> : null}
      {f.stage === 'sent' ? <span className="ern-acts"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => go('won')} data-testid="ern-won">I won it</button></span> : null}
      {f.stage === 'won' || f.stage === 'work' ? <><p className="ern-say">{f.stage === 'won' ? 'Both minds do the work blind with the kits; the Collective checks it. Nothing is delivered.' : 'The work is done; no judge answered yet. Check it again.'}</p><button type="button" className="m-btn m-go" disabled={busy} onClick={() => act({ op: 'earn_work', job: f.id })} data-testid="ern-work">{f.stage === 'won' ? 'Do the work' : 'Check it again'}</button></> : null}
      {f.work?.text ? <details className="ern-work" open={f.stage === 'checked'}><summary>The deliverable · Mind {'AB'[(f.work.mind || 0) % 2]} · Collective {f.collective?.verdict || '—'} {f.collective?.score != null ? `${f.collective.score}/100` : ''}</summary><pre>{f.work.text}</pre></details> : null}
      {f.stage === 'checked' ? <button type="button" className="m-btn m-go" disabled={busy || (test && !real)} onClick={() => go('delivery_approved', { real })} data-testid="ern-deliver">Approve the delivery</button> : null}
      {f.stage === 'delivery_approved' ? <div className="ern-paid"><input className="m-input" inputMode="decimal" value={amt} onChange={e => setAmt(e.target.value)} placeholder="Paid to you" aria-label="Amount paid" data-testid="ern-amt" />
        <input className="m-input" inputMode="decimal" value={fee} onChange={e => setFee(e.target.value)} placeholder="Platform fee" aria-label="Platform fee" /><input className="m-input" value={cur} onChange={e => setCur(e.target.value)} aria-label="Currency" />
        <button type="button" className="m-btn m-go" disabled={busy || !amt} onClick={() => go('paid', { amount: amt, fee: fee || 0, currency: cur })} data-testid="ern-paid">Mark paid</button></div> : null}
      {!ended && f.stage !== 'paid' && f.stage !== 'bid' ? <span className="ern-acts"><input className="m-input" value={why} onChange={e => setWhy(e.target.value)} placeholder="Why it was lost or unpaid" aria-label="Why" />
        <button type="button" className="m-btn" disabled={busy || !why} onClick={() => go(f.stage === 'delivery_approved' ? 'unpaid' : 'lost', { why })} data-testid="ern-lost">{f.stage === 'delivery_approved' ? 'Mark unpaid' : 'Mark lost'}</button></span> : null}
      {g ? <p className={`ern-grade is-${g.result}`} data-testid="ern-grade"><b>{g.result.toUpperCase()}</b> profit <span className="m-num">{usd(g.profit)}</span> · {g.why}</p> : null}
    </section>
  </div>;
}

export function useEarn(cat, work) {
  const [v, setV] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const call = useCallback(async body => { setBusy(true); setErr(''); try { const j = await work(cat.id, body); setV(j); return j; } catch (e) { setErr(e.message); return null; } finally { setBusy(false); } }, [work, cat.id]);
  useEffect(() => { call({ op: 'earn_view' }); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!v?.busy) return undefined; const t = setInterval(() => work(cat.id, { op: 'earn_view' }).then(setV).catch(() => {}), 5000); return () => clearInterval(t); }, [v?.busy, cat.id, work]);
  return { v, busy: busy || !!v?.busy, err, call };
}
