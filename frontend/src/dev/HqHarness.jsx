import React from 'react';
import { AgentDesk } from '../components/command/AgentDesk';
import { RpcKey } from '../components/command/FuseWallet';
import { D } from '../components/command/__fixtures__/cockpit';
import office from '../components/command/__fixtures__/office.json';
import { hubLoad } from '../lib/agentHub';
import { HqDeck } from '../components/command/HqDeck';
import '../styles/hqPop.css';

// 🧪 DEV ONLY (`/dev/hq`, never in a production build — index.js imports it behind NODE_ENV): HQ › Sicario's on the test fixtures, no wallet,
// no signed session. Lets anyone (or Claude) click every Agents-tab control in a real browser and hit-test it — the owner shouldn't have to
// sign in for a layout bug to be found. Writes answer {ok:true} locally; nothing reaches the server.
// seat 1 rides a REAL pool so the live chart (toolbar, grab lines, pins) draws over the cockpit exactly as it does for the owner
// Desktop visual QA can exercise the actual touch layout without changing production device detection.
if (new URLSearchParams(window.location.search).has('touch')) {
  const media = window.matchMedia.bind(window);
  window.matchMedia = query => query === '(pointer: coarse)' ? { matches: true } : media(query);
}
const qa = new URLSearchParams(window.location.search);
if (qa.has('day')) document.body.classList.add('theme-day');
if (qa.has('lite')) document.body.classList.add('fx-lite');
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
// 🔌 ?rpc = HQ › Core › Lag catcher's RPC lanes on fixtures (one live, one out of quota, four empty)
const RPC = { needsKey: false, slots: [1, 2, 3, 4, 5, 6].map(n => ({ slot: n, set: n <= 2 })),
  lanes: [{ lane: 1, slot: 1, provider: 'helius-rpc.com', spent: true, backInMin: 420 }, { lane: 2, slot: 2, provider: 'quiknode.pro', spent: false, backInMin: 0 }] };
// 📸 ?snap = the LIVE desk: copy backend/data/agents_view.json → frontend/public/dev-agents.json (gitignored) to see the owner's real cockpit
const SNAP = new URLSearchParams(window.location.search).has('snap');
const call = async path => (path === '/admin/agents' ? (SNAP ? (await fetch('/dev-agents.json')).json() : live()) : path === '/admin/rpc' ? RPC : { ok: true });
window.__hubLoad = hubLoad;

// 🗂 ?deck=<tab> = the WHOLE HQ deck (every group, every tab) with a fake signed session: every /api/reputation/admin/* read answers from
// fixtures (agents, rpc) or an EMPTY body — the missing-data state each tab must survive (no NaN, no undefined, no '—' walls, no crash).
// Writes answer {ok:true}; public market reads pass through to the dev proxy. `?deck=fuse&grp=Build` lands on that tab.
const DECK = qa.get('deck');
const FAKE = 'HQdev1111111111111111111111111111111111111';
if (DECK) {
  try { localStorage.setItem('feeless:cc-session', JSON.stringify({ address: FAKE, ts: Math.floor(Date.now() / 1000), sig: 'dev' })); localStorage.setItem('feeless.hq.tab', JSON.stringify(DECK)); } catch { /* private */ }
  const real = window.fetch.bind(window);
  const answer = body => Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }));
  window.fetch = (u, o = {}) => {
    const url = String(u?.url || u); const m = url.match(/\/api\/reputation(\/admin\/[^?]*|\/admin)/);
    if (!m) return real(u, o);
    const path = m[1];
    if ((o.method || 'GET') !== 'GET') return answer({ ok: true });
    if (path.startsWith('/admin/is-admin')) return answer({ owner: true, admin: true });
    if (path === '/admin/roles') return answer({ yourRole: 'owner', roles: [] });
    if (path === '/admin/agents') return answer(live());
    if (path === '/admin/rpc') return answer(RPC);
    return answer({});
  };
}

export default function HqHarness() {
  if (DECK) return <div className="hqp is-idle" data-testid="hq-pop" role="dialog" aria-label="HQ (dev preview)"><div className="hqp-body">
    <HqDeck address={FAKE} signMessage={async () => 'dev'} onClose={() => {}} startTab={DECK} /></div></div>;
  return <div className="hqp is-idle" data-testid="hq-pop" role="dialog" aria-label="HQ (dev preview)">
    <header className="hqp-bar"><span className="hqp-mark" aria-hidden="true"><i /><i /><b>HQ</b></span><span className="hqp-mood"><b>🧪 DEV PREVIEW</b><small>fixture data · no sign-in</small></span></header>
    <div className="hqp-body"><div className="cc-shell" data-testid="hq-shell">{window.location.search.includes('rpc') ? <RpcKey call={call} /> : <AgentDesk call={call} isOwner />}</div></div>
  </div>;
}
