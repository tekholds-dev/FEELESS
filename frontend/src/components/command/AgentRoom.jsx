import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import '../../styles/agentRoom.css';

// 🛰 THE AGENT ROOM (owner, 2026-10-09: "an actual box, animated, realistic, no lag, interactive — pops out — click an agent to see its tasks,
// rulings, meta stuff"). Everything in it is the last REAL pass of the desk:
//   · four stations (Tally → Sherlock → Trigger → Devil) with their live task line, generation and life, a ring that turns at the speed
//     of the agent's real work (its ms this pass)
//   · packets = the real coins of this pass travelling the chain, coloured by how they ended (🟢 GO · ✕ objected · ⏳ wait · ⛔ skip)
//   · click a station → its task, its ACTUAL rules (served from the code's constants), its last rulings, its record, lessons, history line
// Pop out = the same room full-screen (Esc / ✕ closes). Transform + opacity only; `.agr` is an fxPause surface; fx-lite stills it.
export const AGENTS = [['tally', '📊', 'Tally', 'numbers'], ['sherlock', '🔍', 'Sherlock', 'why'], ['trigger', '⏱', 'Trigger', 'when'], ['devil', '⚖', 'Devil', 'argues']];
export const packetsOf = table => (table || []).slice(0, 8).map(x => ({ k: x.mint, sym: x.symbol,
  end: x.go ? 'go' : x.trigger?.[0] === 'enter' ? 'obj' : x.trigger?.[0] === 'skip' ? 'skip' : 'wait' }));
const END = { go: '🟢', obj: '✕', wait: '⏳', skip: '⛔' };
const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - t)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
// a speed for each ring: more real ms this pass → a busier (faster) ring, bounded so it never strobes
export const spinSec = ms => Math.max(1.2, Math.min(8, 8 - Math.log10(1 + Math.max(0, Number(ms) || 0)) * 3));

function Spark({ hist, agent }) {
  const pts = (hist || []).map(h => h[agent]).filter(Boolean).map(h => (h.right != null ? Number(h.right) : h.med != null ? 50 + Number(h.med) * 5 : null)).filter(v => v != null);
  if (pts.length < 2) return <small className="m-dim">history fills in every 30 min</small>;
  const w = 220, h = 44; const lo = Math.min(...pts, 40), hi = Math.max(...pts, 60);
  const xy = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${h - ((v - lo) / Math.max(1, hi - lo)) * h}`).join(' ');
  return <svg className="agr-spark" viewBox={`0 0 ${w} ${h}`} data-testid={`spark-${agent}`}><line x1="0" x2={w} y1={h - ((50 - lo) / Math.max(1, hi - lo)) * h} y2={h - ((50 - lo) / Math.max(1, hi - lo)) * h} className="agr-spark-mid" /><polyline points={xy} /></svg>;
}

export function AgentDetail({ d, agent }) {
  const card = (d?.agents || []).find(a => a.key === agent) || {}; const life = d?.life?.[agent] || {};
  const lines = (d?.thoughts || []).filter(l => l.who === agent).slice(0, 6);
  return <div className="agr-detail" data-testid={`agr-detail-${agent}`}>
    <b>{card.icon} {card.name} <small>gen {life.gen || 1} · {life.status || 'alive'} · {d?.perf?.[agent] != null ? `${d.perf[agent]} ms this pass` : '—'}</small></b>
    <p className="agr-now">⚙ {d?.tasks?.[agent] || 'waiting for the first pass'}</p>
    <h6>📏 RULES IT RUNS ON (from the code)</h6><ul>{(d?.rules?.[agent] || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
    <h6>🗯 LAST RULINGS</h6><ul>{lines.length ? lines.map((l, i) => <li key={i}><small>{ago(l.at)}</small> {l.text}</li>) : <li className="m-dim">nothing said yet</li>}</ul>
    <h6>📈 RECORD · this life</h6><p>{card.n ? `${card.n} judged · ${card.med >= 0 ? '+' : ''}${card.med}% typical${card.right != null ? ` · ${card.right}% right` : ''}` : 'no judged calls yet'}</p>
    <Spark hist={d?.hist} agent={agent} />
    {(d?.lessons?.[agent]?.words || []).length > 0 && <><h6>🧬 CARRIES FROM ITS LAST LIFE</h6><p>{d.lessons[agent].words.join(' · ')}</p></>}
  </div>;
}

export function AgentRoom({ d }) {
  const [sel, setSel] = useState('tally'); const [pop, setPop] = useState(false);
  useEffect(() => { if (!pop) return undefined; const k = e => e.key === 'Escape' && setPop(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [pop]);
  const pk = packetsOf(d?.table); const at = d?.perf?.at || 0;
  const room = big => <div className={`agr ${big ? 'is-big' : ''}`} data-testid={big ? 'agr-pop' : 'agr'}>
    <div className="agr-stage">
      <div className="agr-track" aria-hidden><i /></div>
      <div className="agr-packets" key={at} aria-hidden>{pk.map((p, i) => <span key={p.k} className={`agr-pk is-${p.end}`} style={{ '--i': i }}>{END[p.end]} ${p.sym}</span>)}</div>
      {AGENTS.map(([k, ic, name, job], i) => { const l = d?.life?.[k] || {}; const ms = d?.perf?.[k];
        return <button key={k} type="button" className={`agr-st is-${k} is-${l.status || 'alive'} ${sel === k ? 'is-sel' : ''}`} style={{ '--x': i, '--spin': `${spinSec(ms)}s` }}
          onClick={() => setSel(k)} aria-pressed={sel === k} data-testid={`agr-st-${k}`}>
          <span className="agr-ring" aria-hidden /><span className="agr-ava">{ic}</span>
          <b>{name}</b><small>{job} · gen {l.gen || 1}{l.status === 'probation' ? ' ⚠' : l.status === 'scrap' ? ' ☠' : ''}</small>
          <em className="agr-bubble">{(d?.tasks?.[k] || '…').split(' · ')[0]}</em></button>; })}
    </div>
    <AgentDetail d={d} agent={sel} />
  </div>;
  return <section className="agr-wrap" data-testid="agent-room"><div className="agr-head"><b>🛰 THE AGENT ROOM · live</b><small>last pass {at ? `${ago(at)} ago` : '—'} · tap an agent</small>
    <button type="button" className="m-btn agr-out" onClick={() => setPop(true)} data-testid="agr-popout">⤢ Pop out</button></div>
    {room(false)}
    {pop && createPortal(<div className="agr-shade" onClick={e => e.target === e.currentTarget && setPop(false)} role="dialog" aria-label="The agent room">
      <div className="agr-modal"><button type="button" className="agr-x" onClick={() => setPop(false)} aria-label="Close" data-testid="agr-close">✕</button>{room(true)}</div></div>, document.body)}
  </section>;
}
