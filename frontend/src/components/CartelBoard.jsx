import React, { useMemo, useState } from 'react';
import { useGlide } from '../lib/useGlide';
import '../styles/cartelBoard.css';

// ⚖ THE CARTEL WAREHOUSE (owner 2026-10-27: "can't raid the bad guys from rep — they have no city"): every crew FEELESS's own rep flagged
// (bundlers · snipers · funders, grouped by the coins they hit together) — not just the 6 strongest that stand as buildings in Cartel Docks.
// Each one: its live size + strikes, its power against the strongest, and ⚔ RAID right here (×1.5 justice, from ANY city — family_world.can_raid);
// the ones with a building also fly you to it. Raids are the same chess game on their block (RaidStage).
const ROLES = [['all', 'ALL'], ['bundler', '📦 BUNDLERS'], ['sniper', '🎯 SNIPERS'], ['funder', '💸 FUNDERS']];
const n0 = v => (v == null ? '—' : Math.round(Number(v)).toLocaleString('en-US'));

function Total({ label, v, tip, i }) {
  const g = useGlide(v || 0, 700);
  return <span style={{ '--i': i }} data-tip={tip}><em>{label}</em><b className="m-num">{n0(g)}</b></span>;
}

export function CartelBoard({ v, me, act, busy, onFly }) {
  const [role, setRole] = useState('all');
  const cs = v?.cartels || [];
  const blockOf = useMemo(() => Object.fromEntries((v?.blocks || []).filter(b => b.kind === 'cartel' && b.owner).map(b => [b.owner, b.id])), [v]);
  const top = Math.max(1, ...cs.map(c => c.power || 0));
  const rows = cs.filter(c => role === 'all' || c.role === role).slice().sort((a, b) => (b.power || 0) - (a.power || 0));
  const sum = k => cs.reduce((a, c) => a + (Number(c[k]) || 0), 0);
  const why = !me ? 'Join a family to raid' : !me.hitters?.length ? 'Hire a ready hitter on your block first' : null;
  return <div className="cw" data-testid="cartel-board">
    <div className="cw-vitals">
      <Total i={0} label="CARTELS" v={cs.length} tip="Crews FEELESS's rep flagged — every one is raidable" />
      <Total i={1} label="WALLETS" v={sum('members')} tip="Flagged wallets across every cartel" />
      <Total i={2} label="STRIKES" v={sum('hits')} tip="Times they hit a launch (bundled, sniped or funded it)" />
      <Total i={3} label="ACTIVE 7D" v={sum('active7d')} tip="Their wallets seen in the last 7 days" />
      <span className="cw-justice" style={{ '--i': 4 }} data-tip="A raid on a cartel pays ×1.5 loot — justice. Rug Shield HQ hunts them from every city, so reach never blocks it"><em>JUSTICE</em><b>×1.5</b></span>
    </div>
    <span className="m-seg cw-roles" role="radiogroup" aria-label="Cartel kind">{ROLES.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={role === k} className={role === k ? 'active' : ''} onClick={() => setRole(k)} data-testid={`cw-role-${k}`}>{l}</button>)}</span>
    <div className="fwd-carts">{rows.map((c, i) => { const bid = blockOf[c.id]; return <div key={c.id} className={`fwd-cart r-${c.role}`} style={{ '--i': Math.min(i, 12) }} data-testid={`cartel-${c.id}`}>
      <header><i>{c.icon}</i><b>{c.name}</b><small>[{c.tag}] · level {c.level}</small></header>
      <span><em>WALLETS</em><b>{n0(c.members)}</b></span><span><em>HITS</em><b>{n0(c.hits)}</b></span><span><em>COINS</em><b>{n0(c.coins)}</b></span><span><em>ACTIVE 7D</em><b>{n0(c.active7d)}</b></span>
      <u><s style={{ transform: `scaleX(${Math.min(1, c.level / 10)})` }} /></u>
      <p className="cw-power" data-tip={`Power ${n0(c.power)} — its guards and stash grow with it`}><em>POWER</em><i aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, (c.power || 0) / top)})` }} /></i><b className="m-num">{n0(c.power)}</b></p>
      <div className="cw-acts">
        <button type="button" className="m-btn m-go" disabled={busy || !!why} onClick={() => act({ act: 'raid', vs: c.id }, `Raid on ${c.name} started — make your move`)}
          data-tip={why || `A raid is a chess game on their block: your move, theirs, 2+ rounds — loot pays ×1.5 (justice)`} data-testid={`cw-raid-${c.id}`}>⚔ RAID · ×1.5</button>
        {bid && onFly ? <button type="button" className="m-btn" onClick={() => onFly(bid)} data-tip="Fly to their building in Cartel Docks" data-testid={`cw-fly-${c.id}`}>🗺 Their block</button> : null}
      </div></div>; })}</div>
    {!cs.length ? <p className="m-dim">The rep engine has no cartel big enough right now.</p> : null}
  </div>;
}
