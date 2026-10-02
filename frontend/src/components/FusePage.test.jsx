import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'MeWa11et' } }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess' }));
jest.mock('./FuseLab', () => ({ FuseLab: p => <div data-testid="lab" data-copy={p.incoming?.copyOf ? `${p.incoming.copyOf}:${p.incoming.owner}` : ''} data-back={p.incoming?.backKey || ''}>picks:{p.runnerPicks.length}</div> }));
jest.mock('./FuseSide', () => ({ FuseSide: () => null }));
jest.mock('./EcosystemChat', () => ({ __esModule: true, default: ({ room }) => <div data-testid="chat-room">{room}</div> }));
jest.mock('./FuseCard', () => ({ LiveFuseCard: ({ r }) => <div data-testid={`live-${r.id}`} />, FuseCard: ({ c, aura }) => <div className="fcd-mock" data-aura={aura} data-n={c.legs.length} /> }));
jest.mock('./FuseGo', () => ({ FuseGo: p => <div data-testid="fusego" data-side={p.side} data-n={(p.orders || []).length} /> }));
// eslint-disable-next-line import/first
import { FusePage, togglePick, collectSplit, filterBySource } from './FusePage';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const ROW = { id: 'c1', name: 'Core', closed: false, legs: [{ pairAddress: 'P1', symbol: 'AAA', mint: 'M1', tokens: 10, usd: 50, heldUsd: 75, priceNow: 7.5 }, { pairAddress: 'P2', symbol: 'BBB', mint: 'M2', tokens: 5, usd: 50, heldUsd: 75, priceNow: 15 }], drift: 0 };
const PICKS = [1, 2, 3, 4].map(i => ({ mint: `R${i}`, symbol: `RUN${i}`, lane: 'runner', score: 80, mcap: 50000, chg1h: 12, buyShare: 60 }));
const RUNNERS = { round: { picks: PICKS, swaps: [{ at: 5, out: { symbol: 'OLD' }, in: { symbol: 'RUN1' }, why: ['top10 41% > 30%'] }] }, live: [{ mint: 'LV1', symbol: 'LIVE', score: 70, stage: 'graduated' }], proof: { lights: true, rounds: 9, avgPct: 12, winRate: 60, per1: 1.12 },
  lightMinRounds: 8, exits: { scalp: 'x', runner: 'y', hold: 'z' }, nextRoundAt: 9e9, dropped: [], history: [], seen: 4, gates: ['g'], solUsd: 200,
  litCards: [{ id: 'L1', at: 1700000000, picks: PICKS.slice(0, 2), proof: { avgPct: 12, winRate: 60 }, pct: 34.5 }] };
const BATTLES = { endsAt: 9e9, pairs: [{ a: { key: 'user:U1', name: 'Degen card', emoji: '🃏', start: 0, now: 6.2, backers: 3, paidUsd: 40, paidN: 2 }, b: { key: 'lit:L1', name: 'Lit', emoji: '🔥', start: 0, now: -1.4, backers: 1, paidUsd: 0 } }],
  log: [{ at: 1, a: 'X', b: 'Y', winner: 'X', aMove: 3, bMove: 1 }] };
const ARENA = { battles: BATTLES, bench: [{ kind: 'scenario', bench: true, id: 'scen-1', name: 'Moon Mission', emoji: '🚀', dial: 'degen', cfg: { tp: 200, sl: 40, rotateHours: 1, slMode: 'sell' },
  legs: [{ pairAddress: 'PS', symbol: 'SOL', weight: 35 }, { pairAddress: 'PR', symbol: 'R', weight: 65, runner: true }], index: 104, activity: { score: 31, tier: 'calm' }, chat: 'fuse-card-scen-1' }], board: [{ style: 'yield', runs: 3, avgPct: 2, winRate: 66 }], outlook: { note: 'n' }, minSettled: 3, mega: [
  { kind: 'mega', id: 'M1', name: 'Mega', emoji: '⚛️', legs: PICKS.map(p => ({ pairAddress: `P${p.mint}`, symbol: p.symbol, weight: 25 })), index: 120, grade: 'A', buyers: 5, activity: { score: 90, tier: 'blazing' } },
  { kind: 'user', id: 'U1', name: 'Degen card', emoji: '🃏', owner: '@chad', legs: PICKS.slice(0, 3).map(p => ({ pairAddress: `P${p.mint}`, symbol: p.symbol, weight: 33 })), index: 140, grade: 'A', buyers: 1, mode: 'swap',
    activity: { score: 70, tier: 'hot' }, streak: { swaps: 3, won: true, tier: 'phoenix', label: '🔥 Phoenix', bonus: 15 }, copies: 2, copyPct: 10,
    compound: { compounds: 3, tier: 'snowball', label: '❄ Snowball', bonus: 15 }, chat: 'fuse-card-u1' },
  { kind: 'feecat', id: 'feecat', name: "Fee's book", emoji: '🐱', legs: [{ pairAddress: 'PF', symbol: 'UDR', entry: 0.0074, weight: 100 }], index: 92, grade: 'A', buyers: 0,
    activity: { score: 20, tier: 'calm' }, record: { winRate: 61, realizedSol: 0.31, lives: 8 }, chat: 'fuse-card-feecat' },
  { kind: 'lit', id: 'L1', name: '$RUN1 · $RUN2', emoji: '🔥', legs: PICKS.slice(0, 2).map(p => ({ pairAddress: `P${p.mint}`, baseAddress: p.mint, symbol: p.symbol, weight: 50 })), index: 134.5, grade: 'A', buyers: 0, activity: { score: 30, tier: 'warm' } }] };
const SEASON = { week: 1790553600, endsAt: 9e9, cards: 4, boostPct: 10, feecat: { pct: 7.5, winPts: 8 }, board: [
  { rank: 1, id: 'S1', name: 'Moon card', handle: '@chad', pnlPct: 88, beatsCat: true, streak: { swaps: 1, tier: 'survivor', label: '🛡 Survivor', bonus: 5 } },
  { rank: 2, id: 'S2', name: 'Deep', handle: '@ann', pnlPct: 12 }, { rank: 4, id: 'S4', name: 'Down bad', handle: '@x', pnlPct: -9 }],
  moves: [{ id: 'S1', name: 'Moon card', handle: '@chad', from: 3, to: 1, kind: 'up', pnlPct: 88, at: 5 }],
  past: [{ week: 1789948800, top: [{ rank: 1, handle: '@og', pnlPct: 140, wallet: 'W' }] }] };
const SRC = { arena: '🏟 Arena pick', lit: '🔥 Lit card', pump: '🚀 Pump scan', snipers: '🎯 Snipers out', creator: "📣 Creators' pick" };
const DISCOVER = { runners: PICKS.map((p, i) => ({ ...p, sources: i ? [{ kind: 'pump', label: SRC.pump, detail: 'top score' }] : [{ kind: 'arena', label: SRC.arena, detail: 'round' }, { kind: 'pump', label: SRC.pump, detail: 'top' }] })),
  counts: { arena: 1, pump: 4 }, sources: SRC, nextRoundAt: 9e9, gates: ['a', 'b', 'c'], swaps: RUNNERS.round.swaps };

beforeEach(() => {
  window.history.replaceState(null, '', '/terminal/fuse');
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => (String(url).includes('/runners/discover') ? DISCOVER : String(url).includes('/runners') ? RUNNERS : String(url).includes('/fuses/arena') ? ARENA : String(url).includes('/fuses/season') ? SEASON : String(url).includes('/fuses/pnl') ? { pnlUsd: 50, pnlPct: 50, valueUsd: 150, rows: [ROW] }
    : String(url).includes('/balance/') ? { raw: '10000000000', decimals: 9 } : String(url).includes('/limits/') ? { open: 1, max: 2, canOpen: true } : { fuses: [] }) }));
});

test('runner picks cap at 3 and toggle off', () => {
  const r = i => ({ mint: `R${i}` });
  let p = []; [1, 2, 3, 4].forEach(i => { p = togglePick(p, r(i)); });
  expect(p.map(x => x.mint)).toEqual(['R1', 'R2', 'R3']);
  expect(togglePick(p, r(2)).map(x => x.mint)).toEqual(['R1', 'R3']);
  expect(collectSplit(33.3, ROW.legs).every(l => l.pct === 33.3)).toBe(true);
});

test('Fuse 🧬: tabs, runners carry into the Lab, My cards shows every action', async () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick();
  expect(host.querySelector('[data-testid="lab"]').textContent).toBe('picks:0');
  act(() => host.querySelector('[data-testid="fuse-tab-runners"]').click()); await tick();
  ['R1', 'R2', 'R3'].forEach(m => act(() => host.querySelector(`[data-testid="runner-add-${m}"]`).click()));
  expect(host.querySelector('[data-testid="runner-add-R4"]').disabled).toBe(true);           // card full
  act(() => host.querySelector('[data-testid="runners-to-lab"]').click()); await tick();
  expect(host.querySelector('[data-testid="lab"]').textContent).toBe('picks:3');
  act(() => host.querySelector('[data-testid="fuse-tab-cards"]').click()); await tick(); await tick();
  ['take', 'yield', 'rebalance', 'switch', 'limits', 'withdraw'].forEach(k => expect(host.querySelector(`[data-testid="act-${k}-c1"]`)).not.toBeNull());
  expect(host.querySelector('[data-testid="mode-hold-c1"]').getAttribute('aria-checked')).toBe('true');   // cards hold together by default
  expect(host.querySelector('[data-testid="mode-swap-c1"]')).not.toBeNull();
  await act(async () => host.querySelector('[data-testid="act-yield-c1"]').click());
  expect(host.querySelector('[data-testid="act-panel-yield"]').textContent).toContain('33.3% of each leg');   // +50% → sell only the gain
  expect(host.querySelector('[data-testid="yield-lvl-100"]')).not.toBeNull();                                      // Cmd Ctr levels, picked not typed
  expect(host.querySelector('[data-testid="act-panel-yield"]').textContent).toContain('price move only — card P&L never mixes in fees');
  await act(async () => host.querySelector('[data-testid="act-limits-c1"]').click()); await tick();
  expect(host.querySelector('[data-testid="leglim-tp-P1"]')).not.toBeNull();                   // per-coin TP / SL on the card
  await act(async () => host.querySelector('[data-testid="act-withdraw-c1"]').click()); await tick();
  expect(host.querySelector('[data-testid="fusego"]').dataset.side).toBe('sell');
});

test('alert link ?collect=<id>&pct= opens a pre-filled Collect profit', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=cards&collect=c1&pct=33.3');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick(); await tick();
  const panel = host.querySelector('[data-testid="act-panel-take"]');
  expect(panel).not.toBeNull();
  expect(panel.textContent).toContain('33.3%');
  expect(host.querySelector('[data-testid="fusego"]').dataset.n).toBe('2');                    // both legs, sell 33.3% each
});

test('discovery filters by source; multi-source runners glow', async () => {
  expect(filterBySource(DISCOVER.runners, 'arena').map(r => r.mint)).toEqual(['R1']);
  expect(filterBySource(DISCOVER.runners, 'all')).toHaveLength(4);
  window.history.replaceState(null, '', '/terminal/fuse?tab=runners');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick();
  expect(host.querySelector('[data-testid="runner-R1"]').className).toContain('is-hot');
  expect(host.querySelector('[data-testid="runner-R2"]').className).not.toContain('is-hot');
  expect(host.textContent).toContain('$OLD → $RUN1');                                          // auto-swap ticker
  act(() => host.querySelector('[data-testid="src-arena"]').click());
  expect(host.querySelector('[data-testid="runner-R2"]')).toBeNull();
});

test('Arena stage: mega + lit cards with activity effects; lit card → runner picks, mega → Lab; runners show below', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const stage = host.querySelector('[data-testid="arena-stage"]');
  expect(stage.querySelector('[data-testid="mega-M1"]').className).toContain('t-blazing');
  expect(stage.querySelectorAll('[data-testid="mega-M1"] .ar-embers i')).toHaveLength(16);       // hard-coded per tier
  expect(host.querySelector('.fp-arena').className).toContain('ar-tier-blazing');
  expect(host.querySelector('[data-testid="runners"]')).not.toBeNull();                             // old Runners look below
  expect(host.textContent).toContain('auto-swapped');
  act(() => host.querySelector('[data-testid="mega-use-L1"]').click()); await tick();
  expect(host.querySelector('[data-testid="lab"]').textContent).toBe('picks:2');
});

test('Arena: a trader card shows its streak + copies and ⚡ Fuse this too hands the Lab a copy', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const card = host.querySelector('[data-testid="mega-U1"]');
  expect(card.querySelector('[data-testid="streak-phoenix"]').textContent).toContain('Phoenix ×3');
  expect(card.textContent).toContain('⚡ 2 copies'); expect(card.textContent).toContain('swaps weak legs');
  act(() => host.querySelector('[data-testid="mega-use-U1"]').click()); await tick();
  expect(host.querySelector('[data-testid="lab"]').dataset.copy).toBe('U1:@chad');
});

test('Arena: the Fuse season board ranks this week with medals, a countdown and past champions', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const s = host.querySelector('[data-testid="fuse-season"]');
  expect(s.querySelector('[data-testid="season-S1"]').className).toContain('r-1');
  expect(s.querySelector('[data-testid="season-S1"]').textContent).toContain('🥇');
  expect(s.querySelector('[data-testid="season-S4"]').textContent).toContain('#4');
  expect(s.textContent).toContain('PAST CHAMPIONS'); expect(s.textContent).toContain('@og');
});

test('Arena: compound badge, the season race ticker, and 💬 opens that card\'s own chat room', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  expect(host.querySelector('[data-testid="mega-U1"] [data-testid="compound-snowball"]').textContent).toContain('Snowball ×3');
  expect(host.querySelector('[data-testid="season-race"]').textContent).toContain('▲ @chad Moon card #3 → #1');
  await act(async () => host.querySelector('[data-testid="mega-chat-U1"]').click()); await tick();
  expect(host.querySelector('[data-testid="card-chat-U1"] [data-testid="chat-room"]').textContent).toBe('fuse-card-u1');
});

test('Arena: FeeCat\'s sim book is on stage with her record, and ▶ opens a card replay', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const fc = host.querySelector('[data-testid="mega-feecat"]');
  expect(fc.textContent).toContain('sim book · 61% wins · +0.31 SOL realized · ❤8');
  await act(async () => fc.querySelector('[data-testid="mega-replay-feecat"]').click()); await tick();
  expect(host.querySelector('[data-testid="replay-feecat"]')).not.toBeNull();
});

test('Season board: FeeCat\'s week is the bar to beat, and cards above it are marked', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  expect(host.querySelector('[data-testid="season-feecat"]').textContent).toContain('+7.5%');
  expect(host.querySelector('[data-testid="season-S1"]').textContent).toContain('🐱 beat');
  expect(host.querySelector('[data-testid="season-S2"]').textContent).not.toContain('🐱 beat');
});

test('Arena battlefield: pairs fight live (tug-of-war leans to the leader), results log, and each tab explains itself', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const p = host.querySelector('[data-testid="battle-0"]');
  expect(p.className).toContain('a-lead'); expect(p.textContent).toContain('VS'); expect(p.textContent).toContain('+6.2%');
  expect(host.querySelector('[data-testid="battlefield"]').textContent).toContain('🏆 X beat Y');
  expect(host.querySelector('[data-testid="fp-tabtip"]').textContent).toContain('battlefield');
});


test('Arena: runner-up engine cards wear their dial + configs, battles show free vs bought bars, 💰 Buy & back hands the Lab the battle key', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=arena');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick();
  const bench = host.querySelector('[data-testid="arena-bench"]');
  expect(bench.querySelector('[data-testid="mega-scen-1"]').className).toContain('d-degen');
  expect(bench.textContent).toContain('🚀 Moon Mission'); expect(bench.querySelector('[data-testid="cfg-scen-1"]').textContent).toContain('TP +200%');
  expect(host.querySelector('[data-testid="arena-stage"] [data-testid="mega-scen-1"]')).toBeNull();     // runners-up never sit on the stage
  const bars = host.querySelector('[data-testid="bars-0"]');
  expect(bars.textContent).toContain('BUY BACKS 2/0'); expect(bars.textContent).toContain('BACKS 3/1'); expect(bars.textContent).toContain('$40');
  act(() => host.querySelector('[data-testid="buyback-a-0"]').click()); await tick();
  expect(host.querySelector('[data-testid="lab"]').dataset.back).toBe('user:U1');
});
