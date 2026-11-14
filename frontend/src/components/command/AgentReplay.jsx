import React, { useEffect, useMemo, useRef, useState } from 'react';
import { isCalm } from '../../lib/fxPause';
import { KINDS } from './ProofPicker';
import '../../styles/agentReplay.css';

// ⏪ AGX-8 · AGENT REPLAY (owner 2026-11-14): scrub a timeline of what an agent did — your asks, its research, each proof it filed, every buy /
// sell, each grade, each send — and the desk rebuilds itself at that moment (what it had filed by then, its record so far, what it was saying).
// All from its own records (chat, jobs, proof folders); nothing new is stored. Default window: its LAST BUSY DAY (the newest day with at least 6 steps).
const n = v => Number(v) || 0;
const title = (f, kind) => String(f?.topic || f?.name || f?.title || f?.sym || f?.q || '').replace(/\s+/g, ' ').trim().slice(0, 70) || `${kind} #${f?.n || ''}`;
const gradeOf = f => { const g = f?.graded || f?.grade; const s = typeof g === 'object' ? (g?.v || g?.verdict) : g; return s === 'right' || s === 'good' || s === 'won' ? 'right' : s === 'wrong' || s === 'bad' || s === 'lost' ? 'wrong' : null; };
export const EV = { ask: ['🗣', 'You asked'], say: ['🧠', 'It said'], research: ['🔎', 'Research'], file: ['📁', 'Filed'], buy: ['🟢', 'Bought'], sell: ['🔴', 'Sold'], close: ['🏁', 'Closed'], grade: ['⚖', 'Graded'], send: ['📤', 'Sent'] };

/** Pure: every dated thing in an agent's records → events, oldest first. { at, t, text, kind?, win?, id?, tone? } */
export function replayOf(d) {
  const out = []; const add = (at, t, text, x = {}) => { if (n(at) > 0) out.push({ at: n(at), t, text: String(text || '').replace(/\s+/g, ' ').trim().slice(0, 160), ...x }); };
  (d?.chat || []).forEach(m => add(m.at, m.by === 'you' ? 'ask' : 'say', m.text));
  (d?.jobs || []).forEach(j => add(j.at, 'research', `${j.request || 'a task'}${(j.minds || []).length ? ` · ${j.minds.length} minds, ${(j.minds || []).reduce((s, x) => s + (x.steps || []).length, 0)} steps` : ''}`, { win: 'jobs' }));
  KINDS.forEach(({ kind, key, win, ic }) => (d?.[key] || []).forEach(f => {
    const x = { kind, win, id: f.id, ic }; const name = `${kind} #${f.n || '?'} · ${title(f, kind)}`;
    add(f.at, 'file', name, x);
    if (f.boughtAt) add(f.boughtAt, 'buy', `${name}${f.sym ? ` · $${f.sym}` : ''}`, x);
    if (f.soldAt) add(f.soldAt, 'sell', `${name}${f.pnlPct != null ? ` · ${n(f.pnlPct) >= 0 ? '+' : ''}${n(f.pnlPct).toFixed(1)}%` : ''}`, { ...x, tone: n(f.pnlPct) > 0 ? 'right' : n(f.pnlPct) < 0 ? 'wrong' : null });
    if (f.closedAt) add(f.closedAt, 'close', name, x);
    const g = gradeOf(f); if (g) add(n(f.gradedAt) || n(f.closedAt) || n(f.soldAt) || n(f.at) + 1, 'grade', `${name} · ${g}`, { ...x, tone: g });
    if (f.sent) add(n(f.sent?.at) || n(f.sentAt) || n(f.closedAt) || n(f.at) + 2, 'send', name, x);
  }));
  return out.sort((a, b) => a.at - b.at);
}

/** Pure: its last BUSY day — the newest calendar day (its viewer's clock) with at least `min` steps; when none has, its newest day. */
export function lastDay(evs, min = 6) {
  const day = e => new Date(e.at * 1000).toDateString(); const by = new Map();
  evs.forEach(e => { const k = day(e); by.set(k, [...(by.get(k) || []), e]); });
  const days = [...by.values()].reverse();
  return days.find(x => x.length >= min) || days[0] || [];
}

/** Pure: the desk at event i — what it had filed by then, its record, the last line said. */
export function deskAt(evs, i) {
  const upto = evs.slice(0, i + 1); const filed = upto.filter(e => e.t === 'file'); const by = {};
  filed.forEach(e => { by[e.kind] = (by[e.kind] || 0) + 1; });
  const graded = upto.filter(e => e.t === 'grade');
  return { filed, by, right: graded.filter(e => e.tone === 'right').length, wrong: graded.filter(e => e.tone === 'wrong').length,
    trades: upto.filter(e => e.t === 'buy' || e.t === 'sell').length, sent: upto.filter(e => e.t === 'send').length,
    research: upto.filter(e => e.t === 'research').length, said: [...upto].reverse().find(e => e.t === 'say' || e.t === 'ask') || null };
}

const clock = at => new Date(at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
export default function AgentReplay({ d, name, onOpen, onClose }) {
  const all = useMemo(() => replayOf(d), [d]); const [whole, setWhole] = useState(false);
  const evs = useMemo(() => (whole ? all : lastDay(all)), [all, whole]);
  const [i, setI] = useState(() => Math.max(0, evs.length - 1)); const [play, setPlay] = useState(false); const [speed, setSpeed] = useState(1);
  useEffect(() => { setI(Math.max(0, evs.length - 1)); setPlay(false); }, [evs]);
  useEffect(() => { if (!play) return undefined; const t = setInterval(() => setI(x => { if (x >= evs.length - 1) { setPlay(false); return x; } return x + 1; }), 900 / speed); return () => clearInterval(t); }, [play, speed, evs.length]);
  useEffect(() => { const k = e => { if (e.key === 'Escape') { e.stopPropagation(); onClose?.(); } else if (e.key === 'ArrowRight') setI(x => Math.min(evs.length - 1, x + 1)); else if (e.key === 'ArrowLeft') setI(x => Math.max(0, x - 1)); else if (e.key === ' ') { e.preventDefault(); setPlay(p => !p); } };
    window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [evs.length, onClose]);
  const feed = useRef(null);
  useEffect(() => { feed.current?.querySelector('.is-now')?.scrollIntoView?.({ block: 'nearest', behavior: isCalm() ? 'auto' : 'smooth' }); }, [i]);
  const now = evs[i]; const desk = deskAt(evs, i); const t0 = evs[0]?.at || 0; const t1 = evs[evs.length - 1]?.at || 1;
  return <div className="arp" role="dialog" aria-label={`Replay of ${name || 'this agent'}`} data-testid="replay">
    <div className="arp-box">
      <header className="arp-head"><span><small className="m-label">⏪ REPLAY · {whole ? 'EVERYTHING KEPT' : 'ITS LAST BUSY DAY'}</small><b>{name || 'Its desk'}{t0 ? ` · ${new Date(t0 * 1000).toLocaleDateString()}` : ''}</b></span>
        <span className="m-seg" role="group" aria-label="How far back"><button type="button" className={whole ? '' : 'active'} aria-pressed={!whole} onClick={() => setWhole(false)} data-testid="replay-day">Last day</button><button type="button" className={whole ? 'active' : ''} aria-pressed={whole} onClick={() => setWhole(true)} data-testid="replay-all">All</button></span>
        <button type="button" className="m-btn" onClick={onClose} aria-label="Close the replay" data-testid="replay-x">✕</button></header>
      {!evs.length ? <p className="arp-none">Nothing dated to replay yet: its first ask, proof or trade starts the timeline.</p> : <>
        <div className="arp-bar">
          <button type="button" className="m-btn m-go arp-play" onClick={() => { if (i >= evs.length - 1) setI(0); setPlay(p => !p); }} aria-label={play ? 'Pause' : 'Play'} data-testid="replay-play">{play ? '❚❚' : '▶'}</button>
          <div className="arp-track"><div className="arp-ticks" aria-hidden="true">{evs.map((e, k) => <i key={k} className={`is-${e.t}${k <= i ? ' is-past' : ''}`} style={{ left: `${((e.at - t0) / Math.max(1, t1 - t0)) * 100}%` }} />)}</div>
            <input type="range" min={0} max={evs.length - 1} value={i} onChange={e => { setPlay(false); setI(Number(e.target.value)); }} aria-label="Scrub the timeline" aria-valuetext={now ? `${clock(now.at)} ${EV[now.t][1]}` : ''} data-testid="replay-scrub" /></div>
          <b className="m-num arp-clock">{now ? clock(now.at) : ''}</b>
          <span className="m-seg arp-speed" role="group" aria-label="Speed">{[1, 4].map(s => <button key={s} type="button" className={speed === s ? 'active' : ''} aria-pressed={speed === s} onClick={() => setSpeed(s)}>{s}×</button>)}</span></div>
        <div className="arp-two">
          <section className="arp-desk" data-testid="replay-desk"><h4>THE DESK AT {now ? clock(now.at) : ''}<small>{i + 1} of {evs.length}</small></h4>
            <div className="arp-stats">{[['FILED', desk.filed.length], ['RESEARCH', desk.research], ['TRADES', desk.trades], ['RIGHT', desk.right, 'good'], ['WRONG', desk.wrong, 'bad'], ['SENT', desk.sent]].map(([k, v, tone]) => <span key={k} className={tone ? `is-${tone}` : ''}><b className="m-num">{v}</b><small>{k}</small></span>)}</div>
            <ul className="arp-files">{desk.filed.slice(-12).map(e => <li key={`${e.kind}${e.id}`} className={now && now.id === e.id ? 'is-now' : ''}><button type="button" onClick={() => onOpen?.({ win: e.win, id: e.id })} data-tip={`Open ${e.text} in its window`}><i aria-hidden="true">{e.ic}</i><span>{e.text}</span></button></li>)}
              {!desk.filed.length ? <li className="arp-empty">No proof filed yet at this moment</li> : null}</ul>
            {desk.said ? <p className={`arp-said is-${desk.said.t}`}><small>{desk.said.t === 'ask' ? 'YOU' : 'IT'} · {clock(desk.said.at)}</small>{desk.said.text}</p> : null}</section>
          <ol className="arp-feed" ref={feed} data-testid="replay-feed">{evs.map((e, k) => <li key={k} className={`is-${e.t}${k === i ? ' is-now' : ''}${k > i ? ' is-later' : ''}${e.tone ? ` tone-${e.tone}` : ''}`}>
            <button type="button" onClick={() => { setPlay(false); setI(k); }} aria-current={k === i ? 'step' : undefined}><time className="m-num">{clock(e.at)}</time><i aria-hidden="true">{EV[e.t][0]}</i><span><b>{EV[e.t][1]}</b>{e.text}</span></button></li>)}</ol>
        </div></>}
    </div></div>;
}
