import React, { useEffect, useState } from 'react';
import '../../styles/agentPicker.css';

// 🤖 NEW AGENT (owner, 2026-10-22: "create a cat and build a cat showing 2 dif thangs … users pick if they want 1-2 cat AI agents"): ONE door,
// two different agents — the RULE TRADER (free: the Leader's engine on live prices, your name, look and limits) or the AI TRADER (a real model
// brain decides every buy / sell, you read its reasons and talk to it, pay as you go). A user runs at most AGENT_MAX agents. The cat's LOOK is
// its own place: 🎨 Build your cat.
export const AGENT_MAX = 2;
export const AGENT_KINDS = [
  { key: 'create', glyph: 'gear', title: 'Rule trader', tag: 'FREE · PAPER', pitch: "The Leader's engine on live prices — −10 % stop, +22 % take, a trailing stop. You set the name, the look and the limits.",
    meters: [['COST', 0.06, 'free'], ['YOUR CONTROL', 0.92, 'your limits'], ['TALK TO IT', 0.04, 'reads its log']] },
  { key: 'launch', glyph: 'brain', title: 'AI trader', tag: 'PAY AS YOU GO · PAPER', pitch: 'A real model brain decides every buy and sell — one model or two that battle. You read every reason and chime in from its brain panel.',
    meters: [['COST', 0.55, 'per decision'], ['YOUR CONTROL', 0.62, 'its call · your limits'], ['TALK TO IT', 0.95, 'its brain panel']] },
];

function Glyph({ kind }) {
  if (kind === 'gear') {
    const teeth = Array.from({ length: 10 }, (_, i) => <rect key={i} x="45" y="6" width="10" height="16" rx="2" transform={`rotate(${i * 36} 50 50)`} />);
    return <svg className="agp-glyph is-gear" viewBox="0 0 100 100" aria-hidden="true"><g className="spin">{teeth}<circle cx="50" cy="50" r="30" /></g><circle className="hub" cx="50" cy="50" r="12" /></svg>;
  }
  const n = [[30, 30], [70, 26], [50, 50], [24, 68], [76, 66], [50, 80]];
  const l = [[0, 2], [1, 2], [2, 3], [2, 4], [3, 5], [4, 5], [0, 1]];
  return <svg className="agp-glyph is-brain" viewBox="0 0 100 100" aria-hidden="true"><circle className="halo" cx="50" cy="52" r="40" />
    {l.map(([a, b], i) => <line key={i} x1={n[a][0]} y1={n[a][1]} x2={n[b][0]} y2={n[b][1]} />)}{n.map(([x, y], i) => <circle key={i} className="nd" cx={x} cy={y} r={i === 2 ? 7 : 4.5} style={{ '--i': i }} />)}</svg>;
}

export function AgentPicker({ count = 0, onPick }) {
  const [live, setLive] = useState(null);
  useEffect(() => { let on = true; fetch('/api/cats/models').then(r => (r.ok ? r.json() : null)).then(d => { if (on && d) setLive(!!d.live); }).catch(() => {}); return () => { on = false; }; }, []);
  const full = count >= AGENT_MAX;
  return <section className="agp" data-testid="agent-picker">
    <header className="agp-head"><div><span className="eyebrow">NEW AGENT · {count}/{AGENT_MAX} RUNNING</span><h2>Pick the brain your cat trades with.</h2></div>
      <span className="agp-slots" aria-label={`${count} of ${AGENT_MAX} agent slots used`}>{Array.from({ length: AGENT_MAX }, (_, i) => <i key={i} className={i < count ? 'is-used' : ''} />)}</span></header>
    {full ? <p className="agp-full" data-testid="agent-full">You run {AGENT_MAX} agents — retire one in 🤖 My agents to start another.</p> : null}
    <div className="agp-grid">{AGENT_KINDS.map((k, i) => <button key={k.key} type="button" className={`agp-card k-${k.glyph}`} style={{ '--i': i }} disabled={full} onClick={() => onPick(k.key)} data-testid={`agent-${k.key}`}
      data-tip={k.key === 'launch' && live === false ? 'Model calls are switched off right now — it trades on the rule engine until they are on' : k.pitch}>
      <Glyph kind={k.glyph} />
      <span className="agp-tag">{k.tag}</span><b>{k.title}</b><p>{k.pitch}</p>
      <span className="agp-meters">{k.meters.map(([w, v, s], j) => <span key={w} style={{ '--j': j }}><em>{w}</em><i><u style={{ transform: `scaleX(${v})` }} /></i><small>{s}</small></span>)}</span>
      {k.key === 'launch' && live === false ? <span className="agp-off">model calls off — rules until they're on</span> : null}
      <span className="agp-go">Start a {k.title.toLowerCase()} →</span></button>)}</div>
  </section>;
}
