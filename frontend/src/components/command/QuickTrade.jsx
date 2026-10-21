import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Zap } from 'lucide-react';
import { useFloatPop } from '../../lib/floatPop';
import { sharedJson, markFresh } from '../../lib/sharedJson';
import { sellPct } from './MySeat';
import NumInput from '../NumInput';
import '../../styles/quickTrade.css';

// ⚡ QUICK TRADE on every seat card (owner, 2026-10-21: "every trade card needs a quick-trade dropdown — adjust SL, sell X or type a sell amount,
// quick buy — with realtime processing"): one tap opens it on the card. Every button is the card's own existing path (/admin/arena/prime:
// leg sl / tp, manualSell, releaseHeld); the keeper still checks and signs every trade. The steps then follow the REAL leg: sent → saved →
// the keeper moves it (its units change on the card's live read) — never a fake "done".
export const STOPS = [10, 15, 20, 30];
export const TAKES = [25, 50, 100];
export const STEPS = ['sent', 'saved', 'keeper', 'done'];

// pure: where a sell stands — units before vs now (a sell is done when the units fell; a buy when they rose)
export function stageOf(job, units) {
  if (!job) return null;
  if (job.err) return { i: -1, word: job.err };
  if (!job.saved) return { i: 0, word: 'sending…' };
  if (job.kind === 'line') return { i: 3, word: job.word };
  const moved = units != null && job.units0 != null && (job.kind === 'sell' ? units < job.units0 * 0.995 : units > job.units0 * 1.005);
  if (moved) return { i: 3, word: `${job.kind === 'sell' ? 'sold' : 'bought'} — on the card` };
  return { i: 2, word: job.kind === 'sell' ? 'saved — the keeper sells next pass' : 'saved — the keeper buys next pass' };
}

export function QuickTrade({ s, call, tpl }) {
  const fp = useFloatPop(280); const { open, setOpen } = fp;
  const [job, setJob] = useState(null); const [mode, setMode] = useState('%'); const [n, setN] = useState(''); const [leg, setLeg] = useState(null);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  useEffect(() => {
    if (!open && !(job && job.saved && !job.done)) return undefined;
    const read = () => sharedJson('/api/reputation/fuses/prime', { maxAge: 2500 }).then(d => { const c = (d?.cards || []).find(x => x.tpl === tpl); const l = (c?.legs || []).find(x => x.pairAddress === s.pair); if (alive.current) setLeg(l || null); }).catch(() => {});
    read(); const t = setInterval(() => { if (!document.hidden) read(); }, 3000); return () => clearInterval(t);
  }, [open, job, tpl, s.pair]);
  if (!call || !tpl || s.open || !s.pair) return null;
  const units = leg ? Number(leg.units) : null;
  const value = units != null && s.px ? units * Number(s.px) : null;
  const st = stageOf(job, units);
  const send = async (kind, body, word) => {
    setJob({ kind, word, units0: units, saved: false, at: Date.now() });
    try { await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }); markFresh(); if (alive.current) setJob(j => ({ ...j, saved: true })); }
    catch (e) { if (alive.current) setJob(j => ({ ...j, err: String(e?.message || e) })); }
  };
  const pct = sellPct(mode, n, value);
  return <>
    <button type="button" ref={fp.ref} className={`qtr-btn ${st && st.i >= 0 && st.i < 3 ? 'is-busy' : ''}`} aria-expanded={open} onClick={e => { e.stopPropagation(); setOpen(!open); }}
      data-testid={`qtr-${s.symbol}`} aria-label={`Quick trade $${s.symbol}`}><Zap size={13} /></button>
    {open && createPortal(<div ref={fp.popRef} style={fp.style} className="qtr-pop" role="dialog" aria-label={`Quick trade $${s.symbol}`} data-testid="qtr-pop">
      <header><b>⚡ ${s.symbol}</b><span className={s.pct >= 0 ? 'up' : 'dn'}>{s.pct != null ? `${s.pct >= 0 ? '+' : ''}${s.pct.toFixed(1)}%` : '—'}</span><small>{value != null ? `worth $${value.toFixed(2)}` : 'reading…'}</small></header>
      <section><em>🛑 STOP</em><div className="qtr-row">{STOPS.map(v => <button key={v} type="button" className={leg?.sl === v ? 'active' : ''} onClick={() => send('line', { leg: { tpl, pairAddress: s.pair, sl: v } }, `🛑 stop at −${v}%`)} data-testid={`qtr-sl-${v}`}>−{v}%</button>)}</div></section>
      <section><em>🎯 TAKE</em><div className="qtr-row">{TAKES.map(v => <button key={v} type="button" className={leg?.tp === v ? 'active' : ''} onClick={() => send('line', { leg: { tpl, pairAddress: s.pair, tp: v } }, `🎯 take at +${v}%`)} data-testid={`qtr-tp-${v}`}>+{v}%</button>)}</div></section>
      <section><em>✂ SELL</em><div className="qtr-row">{[25, 50, 100].map(v => <button key={v} type="button" className="is-sell" onClick={() => send('sell', { manualSell: { tpl, pairAddress: s.pair, pct: v, ack: true } }, `✂ ${v}%`)} data-testid={`qtr-sell-${v}`}>{v === 100 ? 'ALL' : `${v}%`}</button>)}</div>
        <div className="qtr-amt"><NumInput className="m-input" value={n} onChange={e => setN(e.target.value)} placeholder={mode === '$' ? '$ amount' : '% amount'} aria-label="Sell amount" data-testid="qtr-amt" />
          <button type="button" onClick={() => setMode(m => (m === '%' ? '$' : '%'))} aria-label="Switch % or $">{mode}</button>
          <button type="button" className="is-sell" disabled={!pct} onClick={() => pct && send('sell', { manualSell: { tpl, pairAddress: s.pair, pct, ack: true } }, `✂ ${pct}%`)} data-testid="qtr-amt-go">Sell{pct ? ` ${pct}%` : ''}</button></div></section>
      <section><em>＋ QUICK BUY</em><button type="button" className="qtr-buy" onClick={() => send('buy', { releaseHeld: { tpl, pairAddress: s.pair } }, '＋ held cash into it')} data-testid="qtr-buy"
        data-tip="Puts the cash held for you on the card into this coin — the keeper buys the difference">＋ Put my held cash into ${s.symbol}</button></section>
      {st ? <div className={`qtr-steps ${st.i < 0 ? 'is-bad' : st.i >= 3 ? 'is-done' : 'is-run'}`} data-testid="qtr-steps">
        <ol>{STEPS.map((w, i) => <li key={w} className={st.i > i || st.i === 3 ? 'done' : st.i === i ? 'now' : ''}>{w}</li>)}</ol>
        <span className="qtr-bar"><i /></span><small>{job.word} · {st.word}</small></div> : null}
    </div>, document.body)}
  </>;
}
