import React, { useEffect, useState } from 'react';
import '../../styles/agentPicker.css';

// 🤖 NEW AGENT (owner, 2026-10-23: "TWO KINDS OF AI CAT — user's own wallet, real money, NO paper"): ONE door, two AI cats that both end at
// pick models → its own wallet → REAL (DECISIONS #2: your wallet signs ONE funding, then it trades inside the caps; FEELESS never sees your keys):
//   📈 TRADING AI cat — 1-2 trading models hunt coins for you · 🧭 GENERAL AI cat — 1-2 all-round models do what you order in plain words.
// The free rule trader stays as a 🧪 paper TEST toggle under the two (never the headline). A user runs at most AGENT_MAX agents.
export const AGENT_MAX = 2;
export const AGENT_KINDS = [
  { key: 'trading', glyph: 'brain', title: 'Trading AI cat', tag: 'REAL · ITS OWN WALLET', pitch: '1–2 trading models hunt Solana coins for you from the cat\'s own wallet — you sign ONE funding, then it trades inside the caps you set.',
    meters: [['WHAT IT DOES', 0.9, 'hunts + trades'], ['YOUR CONTROL', 0.85, 'caps + stop'], ['TALK TO IT', 0.95, 'its brain panel']] },
  { key: 'general', glyph: 'orbit', title: 'General AI cat', tag: 'REAL · YOU OK EACH MOVE', pitch: '1–2 all-round models — its two minds answer, research in their own cloud browsers while you watch, and run your coin orders from its own wallet: you OK each move (one tap) until you switch it to auto.',
    meters: [['WHAT IT DOES', 0.95, 'research + orders'], ['YOUR CONTROL', 0.95, 'you OK each'], ['TALK TO IT', 1, 'both minds or one']] },
];

function Glyph({ kind }) {
  if (kind === 'gear') {
    const teeth = Array.from({ length: 10 }, (_, i) => <rect key={i} x="45" y="6" width="10" height="16" rx="2" transform={`rotate(${i * 36} 50 50)`} />);
    return <svg className="agp-glyph is-gear" viewBox="0 0 100 100" aria-hidden="true"><g className="spin">{teeth}<circle cx="50" cy="50" r="30" /></g><circle className="hub" cx="50" cy="50" r="12" /></svg>;
  }
  const n = [[30, 30], [70, 26], [50, 50], [24, 68], [76, 66], [50, 80]];
  const l = [[0, 2], [1, 2], [2, 3], [2, 4], [3, 5], [4, 5], [0, 1]];
  if (kind === 'orbit') {   // 🧭 a core that takes orders: three task moons orbiting it
    return <svg className="agp-glyph is-orbit" viewBox="0 0 100 100" aria-hidden="true"><circle className="ring" cx="50" cy="50" r="36" /><circle className="ring r2" cx="50" cy="50" r="24" />
      <g className="orb">{[0, 120, 240].map((a, i) => <circle key={a} className="moon" r={i ? 4.5 : 6} cx="50" cy="14" transform={`rotate(${a} 50 50)`} />)}</g>
      <circle className="core" cx="50" cy="50" r="11" /><path className="tick" d="M44 50 l4.5 4.5 L57 45" /></svg>;
  }
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
      data-tip={live === false ? 'Model calls are switched off right now — it runs on the rule engine until they are on' : k.pitch}>
      <Glyph kind={k.glyph} />
      <span className="agp-tag">{k.tag}</span><b>{k.title}</b><p>{k.pitch}</p>
      <span className="agp-meters">{k.meters.map(([w, v, s], j) => <span key={w} style={{ '--j': j }}><em>{w}</em><i><u style={{ transform: `scaleX(${v})` }} /></i><small>{s}</small></span>)}</span>
      {live === false ? <span className="agp-off">model calls off — rules until they're on</span> : null}
      <span className="agp-flow" aria-hidden="true"><i>🧠 models</i><u /><i>👛 your wallet</i><u /><i className="is-real">💵 REAL</i></span>
      <span className="agp-go">Start a {k.title.toLowerCase()} →</span></button>)}</div>
    <button type="button" className="agp-test" disabled={full} onClick={() => onPick('create')} data-testid="agent-create"
      data-tip="The free rule trader on paper — the Leader's engine on live prices with your name, look and limits. A test, no wallet">🧪 Test first on paper — free rule trader →</button>
  </section>;
}
