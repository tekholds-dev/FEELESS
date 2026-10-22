import React from 'react';
import { AgentDesk } from '../components/command/AgentDesk';
import { D } from '../components/command/__fixtures__/cockpit';
import office from '../components/command/__fixtures__/office.json';
import { hubLoad } from '../lib/agentHub';
import '../styles/hqPop.css';

// 🧪 DEV ONLY (`/dev/hq`, never in a production build — index.js imports it behind NODE_ENV): HQ › Sicario's on the test fixtures, no wallet,
// no signed session. Lets anyone (or Claude) click every Agents-tab control in a real browser and hit-test it — the owner shouldn't have to
// sign in for a layout bug to be found. Writes answer {ok:true} locally; nothing reaches the server.
// seat 1 rides a REAL pool so the live chart (toolbar, grab lines, pins) draws over the cockpit exactly as it does for the owner
const REAL = new URLSearchParams(window.location.search).get('pair') || 'Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE';
const DATA = JSON.parse(JSON.stringify({ ...D, office: { ...office, ...D.office } }).replaceAll('"P1"', `"${REAL}"`));
let tick = 0;   // every snapshot is a NEW object with moved numbers, like the live desk (window.__hubLoad() forces one)
const live = () => { tick += 1; const j = v => (typeof v === 'number' ? v * (1 + 0.01 * Math.sin(tick)) : v);
  return { ...DATA, card: { ...DATA.card, seats: (DATA.card.seats || []).map(s => ({ ...s, pct: j(s.pct) })) },
    office: { ...DATA.office, positions: (DATA.office.positions || []).map(p => ({ ...p, pct: j(p.pct), last: j(p.last) })), tape: [...(DATA.office.tape || [])] } }; };
const call = async path => (path === '/admin/agents' ? live() : { ok: true });
window.__hubLoad = hubLoad;

export default function HqHarness() {
  return <div className="hqp is-idle" data-testid="hq-pop" role="dialog" aria-label="HQ (dev preview)">
    <header className="hqp-bar"><span className="hqp-mark" aria-hidden="true"><i /><i /><b>HQ</b></span><span className="hqp-mood"><b>🧪 DEV PREVIEW</b><small>fixture data · no sign-in</small></span></header>
    <div className="hqp-body"><div className="cc-shell" data-testid="hq-shell"><AgentDesk call={call} isOwner /></div></div>
  </div>;
}
