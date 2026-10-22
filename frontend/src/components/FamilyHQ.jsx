import React, { useEffect, useRef, useState } from 'react';
import { Armchair, Radio, IdCard, Mail, Flower2, MessagesSquare, Crosshair, Rocket, UserPlus, KeyRound, DoorOpen, MapPinned } from 'lucide-react';
import { FamilyBadge } from './FamilyBadge';
import '../styles/familyHQ.css';

// 🏠 YOUR FAMILY HQ (owner, 2026-10-22: "where do I see my family city and add town expansions … the page of my family should be meta with vitals
// and tools — strip the text, real-time vital animations"): the room that pops out over the city from your block / the directory. No paragraphs:
// the family's live numbers as rings and meters that move when they move, one rail of tools (table, wire, card, invite, badge, board, bounties,
// launch, seats, code), the door to your 3D block, and the turf you can expand into next with its MP price.
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
export function useCount(target, ms = 650) {   // a number glides to its new value (never a jump)
  const [v, setV] = useState(Number(target) || 0); const from = useRef(Number(target) || 0);
  useEffect(() => { const to = Number(target) || 0; const a = from.current; if (a === to) return undefined; const t0 = performance.now(); let raf;
    const step = t => { const k = Math.min(1, (t - t0) / ms); const e = 1 - (1 - k) ** 3; const x = a + (to - a) * e; setV(x); if (k < 1) raf = requestAnimationFrame(step); else from.current = to; };
    raf = requestAnimationFrame(step); return () => { cancelAnimationFrame(raf); from.current = to; }; }, [target, ms]);
  return v;
}
function Ring({ v, max = 100, label, tone = 'gold', fmt = x => n(x) }) {
  const x = useCount(v); const k = Math.max(0, Math.min(1, x / max));
  return <span className={`fhq-ring t-${tone}`} style={{ '--k': k }} data-tip={`${label}: ${fmt(v)}`}><i /><b className="m-num">{fmt(x)}</b><em>{label}</em></span>;
}
function Meter({ label, v, max, txt, tone = '' }) {
  const k = Math.max(0.02, Math.min(1, (Number(v) || 0) / Math.max(1, max)));
  return <span className={`fhq-meter ${tone}`} data-tip={`${label}: ${txt}`}><em>{label}</em><b className="m-num" key={txt}>{txt}</b><u><s style={{ transform: `scaleX(${k})` }} /></u></span>;
}
function Dots({ label, have, of }) {
  return <span className="fhq-dots" data-tip={`${label}: ${have} of ${of}`}><em>{label}</em><span>{Array.from({ length: Math.min(of, 15) }, (_, i) => <i key={i} className={i < have ? 'on' : ''} style={{ '--i': i }} />)}</span><b className="m-num">{have}/{of}</b></span>;
}
export const TOOLS = [['table', 'Table', Armchair], ['wire', 'Wire', Radio], ['card', 'Card', IdCard], ['invite', 'Invite', Mail], ['badge', 'Badge', Flower2], ['board', 'Board', MessagesSquare],
  ['bounty', 'Bounties', Crosshair], ['launch', 'Launch', Rocket], ['members', 'Seats', UserPlus], ['code', 'Code', KeyRound]];

// pure: the turf a family can expand into next — the cheapest free blocks it can afford first
export function nextTurf(me, n_ = 4) {
  return Object.entries(me?.prices || {}).map(([id, mp]) => ({ id, mp: Number(mp) || 0, ok: (Number(mp) || 0) <= (me?.bank || 0) })).sort((a, b) => a.mp - b.mp).slice(0, n_);
}

export function FamilyHQ({ mine, world, act, busy, onEnter, onFly, tools }) {
  const [tool, setTool] = useState('table');
  const vt = mine.vitals || {}; const war = mine.war || {}; const me = world?.me || null;
  const week = useCount(vt.usd || 0); const turfMax = world?.rules?.turfMax || 12; const turf = (me?.turf || []).length + (me?.home ? 1 : 0);
  const next = nextTurf(me);
  return <div className="fhq" data-testid="family-hq">
    <header className="fhq-id">{mine.badge ? <FamilyBadge b={mine.badge} size="sm" /> : <span className="fhq-rose" aria-hidden="true" />}
      <span><b>{mine.name}</b><small>[{mine.tag}] · {mine.members.length}/{mine.seats} seats</small></span>
      <span className={`fhq-week m-num ${week >= 0 ? 'up' : 'dn'}`} data-tip="This week's verified result (price only — fees apart)">{week >= 0 ? '+' : '−'}${Math.abs(week).toFixed(2)}</span></header>
    <div className="fhq-vitals">
      <Ring v={vt.respect || 0} label="RESPECT" />
      <Ring v={vt.wonPct || 0} label="WON" tone="green" fmt={x => `${Math.round(x)}%`} />
      <Ring v={vt.heat || 0} label="HEAT" tone="red" />
      <div className="fhq-grid">
        <Dots label="WORKING 24H" have={vt.active || 0} of={vt.members || mine.members.length} />
        <Meter label="TRADES" v={vt.trades || 0} max={60} txt={n(vt.trades)} />
        <Meter label="WARS" v={war.wins || 0} max={(war.wins || 0) + (war.losses || 0) || 1} txt={`${war.wins || 0}–${war.losses || 0}`} tone="is-red" />
        <Meter label="WAR CHEST" v={war.chest || 0} max={5000} txt={`${n(war.chest)} pts`} tone="is-gold" />
        {me ? <Meter label="MP BANK" v={me.bank || 0} max={Math.max(me.bank || 0, 50000)} txt={`${n(me.bank)} MP`} tone="is-gold" /> : null}
        {me ? <Meter label="TURF" v={turf} max={turfMax} txt={`${turf}/${turfMax}`} /> : null}
      </div>
    </div>
    {me ? <div className="fhq-town" data-testid="family-town"><span className="fhq-label"><MapPinned size={13} aria-hidden="true" /> YOUR TOWN</span>
      <button type="button" className="m-btn m-go" onClick={onEnter} data-tip="Your own 3D block: build the stores, collect the stash, hire the crew" data-testid="hq-enter"><DoorOpen size={14} aria-hidden="true" /> Enter your block</button>
      {me.home ? <button type="button" className="m-btn" onClick={() => onFly?.(me.home)} data-tip="Fly the city camera to your home block" data-testid="hq-fly-home">Fly home · {me.home}</button> : null}
      {next.length ? <ol className="fhq-next">{next.map((b, i) => <li key={b.id} style={{ '--i': i }}><button type="button" className={`m-btn ${b.ok ? '' : 'is-short'}`} disabled={busy || !b.ok} onClick={() => act({ act: 'buy', block: b.id }, `Expanded to ${b.id}`)}
        data-tip={b.ok ? `Expand the town: buy ${b.id} for ${n(b.mp)} MP (+4 % production, +1 recruit seat, more raid reach)` : `Needs ${n(b.mp - (me.bank || 0))} more MP`} data-testid={`hq-expand-${b.id}`}>＋ {b.id}<small>{n(b.mp)} MP</small></button></li>)}</ol> : null}
    </div> : null}
    <nav className="fhq-tools" role="tablist" aria-label="Family tools">{TOOLS.map(([k, label, Icon], i) => <button key={k} type="button" role="tab" aria-selected={tool === k} className={tool === k ? 'active' : ''} style={{ '--i': i }}
      onClick={() => setTool(k)} data-tip={label} data-testid={`hq-tool-${k}`}><Icon size={16} aria-hidden="true" /><span>{label}</span>{k === 'bounty' && mine.bountiesOpen ? <b>{mine.bountiesOpen}</b> : null}</button>)}</nav>
    <div className="fhq-pane" key={tool}>{tools ? tools(tool, setTool) : null}</div>
  </div>;
}
