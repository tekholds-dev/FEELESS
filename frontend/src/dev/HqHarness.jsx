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
// 🧪 A06 the PICK strip on fixtures: the proof gate reads TRADE and the first READY coin is a pick
const EDGE = { on: true, young: false, seatPicksOnly: true, minAgeMin: 15, gate: 'trade', held: 19, tested: 1107, rules: [{ rule: 'top10:35+ + xl:<1', med: 44.6, n: 70, up: 61 }, { rule: 'bund:0 + xl:<1', med: 27.1, n: 105, up: 60 },
  { rule: '5m:5..15 + buy:65+', med: 21.5, n: 62, up: 58 }] };
const PICK = { rule: '5m:5..15 + buy:65+', med: 21.5, n: 62, entry: 'on its germ floor (5% above it)', why: '🧪 PICK 5m:5..15 + buy:65+ (+21.5% typical on 62 unseen coins) · survived 1m +2% · 5m +6% · on its germ floor (5% above it)' };
const picked = k => { let done = false; return { ...k, candidates: ((k || {}).candidates || []).map(c => (!done && c.status === 'READY' && (done = true) ? { ...c, pick: PICK } : c)) }; };
let tick = 0;   // every snapshot is a NEW object with moved numbers, like the live desk (window.__hubLoad() forces one)
const live = () => { tick += 1; const j = v => (typeof v === 'number' ? v * (1 + 0.01 * Math.sin(tick)) : v);
  return { ...DATA, duo: DUO, card: { ...DATA.card, seats: (DATA.card.seats || []).map(s => ({ ...s, pct: j(s.pct) })) },
    office: { ...DATA.office, edge: EDGE, kernel: picked(DATA.office.kernel), positions: (DATA.office.positions || []).map(p => ({ ...p, pct: j(p.pct), last: j(p.last) })), tape: [...(DATA.office.tape || [])] } }; };
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
  const COLONY = { wallet: { address: '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU', at: 1793480000 }, value: { sol: 6.2, usdc: 410, feecatUsd: 380, usd: 1985.4 }, principalUsd: 1500, growthUsd: 485.4, payableUsd: 97.08,
    policy: { epochCapPct: 20, timelockH: 24, cadence: 'daily' }, bounds: { epochCapPct: [5, 50], timelockH: [6, 72] }, guards: ['principalLock', 'allowlist', 'ownerSigns'], stakeMinUsd: 25, colonized: 7, trades: 31, epoch: 20757, left: 3400,
    airdrop: [{ owner: '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM', sol: 0.42, pct: 58.3, usd: 56.6 }, { owner: 'HN7cABqLq46Es1jh92dQQisAq662SmxELLLsHHe4YWrH', sol: 0.3, pct: 41.7, usd: 40.48 }],
    nextAirdrop: Date.now() / 1000 + 5 * 3600, sharers: 2, sharedSol: 0.72, pool: null, poolTokens: [{ k: 'SOL', mint: 'So11111111111111111111111111111111111111112' }, { k: 'USDC', mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' }, { k: 'FEE', mint: 'FeeDev11111111111111111111111111111111111111' }, { k: 'FEECAT', mint: 'CatDev11111111111111111111111111111111111111' }],
    board: [], browsers: ['kernel', 'steel', 'browserless', 'reader'], log: [] };
  window.fetch = (u, o = {}) => {
    const url = String(u?.url || u); const m = url.match(/\/api\/reputation(\/admin\/[^?]*|\/admin)/);
    if (!m) return real(u, o);
    const path = m[1];
    if ((o.method || 'GET') !== 'GET') return answer({ ok: true });
    if (path.startsWith('/admin/is-admin')) return answer({ owner: true, admin: true });
    if (path === '/admin/roles') return answer({ yourRole: 'owner', roles: [] });
    if (path === '/admin/agents') return answer(live());
    if (path === '/admin/rpc') return answer(RPC);
    if (path === '/admin/agent-slots') return answer({ open: 250, taken: 173, left: 77, max: 1000 });   // 🎟 the slots card on a fixture
    if (path === '/admin/collective') return real('/dev-collective.json');   // 💎 the live rules, generated from collective_pool (gitignored)
    if (path === '/admin/colony') return answer(COLONY);   // 🏺 the colony pot on a fixture (the live one needs the owner's session)
    if (SNAP && (path === '/admin/feecat' || path === '/admin/ai/prompts')) return real(`/dev-${path === '/admin/feecat' ? 'feecat' : 'prompts'}.json`);   // 📸 ?snap: Fee's live desk + studio (gitignored copies)
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
