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
// 🔁 the OSSY × G4 seat on fixtures: ?duo=sold (the review minute after a close) · hunt (open seat, hunter's clock) · hold (a live seat trade)
const DUO_AT = Date.now() / 1000;
const DUO_ROOMS = [{ mint: 'J9MT', symbol: 'MOON', model: 'OSSY', closed: true, pct: -8.8, usd: -0.033, inUsd: 0.375, back: 0.342, heldMin: 16.2, at: DUO_AT - 1000,
  rows: [{ at: DUO_AT - 60, model: 'OSSY', action: 'REVIEW', view: 'D', why: '🏁 FINAL on $MOON (-8.8%, peak -0.1%): slid and we sold at a rug-trigger · lesson: set exit levels first', pct: -8.8, talk: true },
    { at: DUO_AT - 240, model: 'G4', action: 'HOLD', why: "OSSY's at -5.8% with negative peak — let it breathe", pct: -5.8 }] }];
const DUO_LOG = [{ at: DUO_AT - 21, model: 'OSSY', action: 'REVIEW', symbol: 'MOON', why: 'FINAL on $MOON', pct: -8.8 }, { at: DUO_AT - 90, model: 'AGENTS', action: 'WAIT', why: 'no model answered' },
  { at: DUO_AT - 150, model: 'G4', action: 'HOLD', symbol: 'MOON', why: 'let it breathe', conf: 86, ms: 23300 }, { at: DUO_AT - 210, model: 'OSSY', action: 'HOLD', symbol: 'MOON', why: 'above germ floor', conf: 63, ms: 31600 }];
const DUO_MODE = new URLSearchParams(window.location.search).get('duo') || 'sold';
const DUO = { mode: 'real', next: 'G4', at: DUO_AT, busy: false, rooms: DUO_ROOMS, log: DUO_LOG, seats: { used: DUO_MODE === 'hold' ? 3 : 2, max: 4 },
  totals: { G4: { n: 77, won: 14, usd: -1.766, pct: -341.8 }, OSSY: { n: 99, won: 26, usd: -0.06, pct: -32.7 } }, agents: { n: 3, won: 33 },
  live: { by: 'G4', at: DUO_AT - 30, cands: [{ symbol: 'LUKE', status: 'READY', move5m: 4.2, buyers: 61, germ: 6 }, { symbol: 'SSB', status: 'CONTENDING', move5m: -1.1, buyers: 54, germ: 11 }] },
  ...(DUO_MODE === 'sold' ? { phase: 'SOLD' } : DUO_MODE === 'hunt' ? { phase: 'HUNTING', hunt: { by: 'G4', since: DUO_AT - 132, turnSec: 600 } }
    : { phase: 'HOLDING', holder: 'G4', holding: { symbol: 'LUKE', mint: 'L', inUsd: 0.31, nowUsd: 0.336, pct: 8.4, pnlUsd: 0.026, peak: 11.2, heldMin: 17, tp: 40, sl: 15 } }) };
let tick = 0;   // every snapshot is a NEW object with moved numbers, like the live desk (window.__hubLoad() forces one)
const live = () => { tick += 1; const j = v => (typeof v === 'number' ? v * (1 + 0.01 * Math.sin(tick)) : v);
  return { ...DATA, duo: DUO, card: { ...DATA.card, seats: (DATA.card.seats || []).map(s => ({ ...s, pct: j(s.pct) })) },
    office: { ...DATA.office, positions: (DATA.office.positions || []).map(p => ({ ...p, pct: j(p.pct), last: j(p.last) })), tape: [...(DATA.office.tape || [])] } }; };
const call = async path => (path === '/admin/agents' ? live() : { ok: true });
window.__hubLoad = hubLoad;

export default function HqHarness() {
  return <div className="hqp is-idle" data-testid="hq-pop" role="dialog" aria-label="HQ (dev preview)">
    <header className="hqp-bar"><span className="hqp-mark" aria-hidden="true"><i /><i /><b>HQ</b></span><span className="hqp-mood"><b>🧪 DEV PREVIEW</b><small>fixture data · no sign-in</small></span></header>
    <div className="hqp-body"><div className="cc-shell" data-testid="hq-shell"><AgentDesk call={call} isOwner /></div></div>
  </div>;
}
