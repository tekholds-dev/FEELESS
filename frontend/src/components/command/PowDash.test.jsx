import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PowDash, powNumbers, guardOf, livePips, basisOf, callWord, GUARD } from './PowDash';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const NOW = 1795100000;
// shaped like Happy's real PoW folders (newest first, as the server sends them)
const PROP = { id: 'p17', n: 17, at: NOW, status: 'closed', propose: true, sym: 'AI', sol: 0.005, tp: 15, sl: 10, test: { agent: 'Happy Assistant' }, cost: 0.06,
  pick: { mint: 'MAI', sym: 'AI' }, coins: [{ mint: 'MAI', sym: 'AI', src: 'pump', liq: 110000, mc: 310000 }, { mint: 'MPIPI', sym: 'PIPI', src: 'pump' }, { mint: 'MDSP', sym: 'DSP', src: 'intake' }],
  dropped: [{ mint: 'MDSP', sym: 'DSP', risk: 'no holder intel yet' }, { mint: 'MQ', sym: 'QUATS', risk: '🚀 +608% in 1h — already ran, that is the top-buyer seat' }],
  talk: [{ by: 'engine', text: 'new folder: $AI', at: NOW + 1 }, { by: 'plan', text: '1) both minds compare', at: NOW + 2 }, { by: 'gpt-6.1-terra', text: '$AI researched on coingecko.com', at: NOW + 3 },
    { by: 'gpt-6.1-terra', text: 'final plan: $AI · 0.005 SOL', at: NOW + 4 }] };
const WIN = { id: 'p10', n: 10, at: NOW - 9000, status: 'closed', sym: 'ANSEM', pnlPct: 9.31, pnlSol: 0.000745, soldAt: NOW - 8000, cost: 0.34, dropped: [{ mint: 'MG', sym: 'GRILL', risk: '🐣 13 min old — under 15 min loses (trench law)' }],
  talk: [{ by: 'glm-5.3-flash', text: 'check 1: HOLD — Chart flat', at: NOW - 8500 }] };
const LOSS = { id: 'p9', n: 9, at: NOW - 20000, status: 'closed', sym: 'GATO', pnlPct: -0.62, pnlSol: -0.00005, soldAt: NOW - 19000, cost: 0.058, pnlBasis: 'pool', dropped: [{ mint: 'MI', sym: 'INU', risk: '💧 pool $4,927 — under the $5,000 floor (you could not get out)' }] };
const FOLDERS = [PROP, WIN, LOSS];

test('pure: P&L without fees from its folders, its curve in order, open work, guard tallies, the minds\' calls', () => {
  const n = powNumbers(FOLDERS);
  expect(n.trades.map(f => f.n)).toEqual([9, 10]);   // oldest sale first: the curve runs forward
  expect(n.pnl).toBeCloseTo(0.000695, 9); expect(n.curve.map(p => p.v)).toEqual([-0.00005, 0.000695]);
  expect(n.winPct).toBe(50); expect(n.best.sym).toBe('ANSEM'); expect(n.cash).toBe(1);   // #10 has only its cash fills (fees in): counted, never hidden
  expect(n.open.map(f => f.id)).toEqual(['p17']);   // the proposal waits for him; a proposal never counts as a trade
  expect(n.byGuard).toEqual({ unread: 1, ran: 1, age: 1, pool: 1 }); expect(n.stops).toHaveLength(4);
  expect(n.calls.map(c => c.text)).toEqual(['final plan: $AI · 0.005 SOL', 'check 1: HOLD — Chart flat']);   // engine, plan and research notes are not calls
  expect(n.watch.map(c => c.mint)).toEqual(['MAI', 'MPIPI']);   // the coin its guard dropped is not watched
  expect(n.cost).toBeCloseTo(0.458, 6);
  expect(powNumbers([]).winPct).toBeNull(); expect(powNumbers([]).pnl).toBe(0);
});

test('pure: guard words, live pips, basis and call words read the server\'s own lines', () => {
  expect(guardOf('🐣 3 min old — under 15 min loses')).toBe('age'); expect(guardOf('💧 pool $0 — under the $5,000 floor')).toBe('pool');
  expect(guardOf('🚀 +563% in 1h — already ran')).toBe('ran'); expect(guardOf('same fingerprint as PoW #15 $Donkey, which lost')).toBe('repeat');
  expect(guardOf('no holder intel yet')).toBe('unread'); expect(guardOf('7 bundled wallets')).toBe('holders');
  const now = 1_800_000_000_000;
  expect(livePips({ liquidity: { usd: 9000 }, pairCreatedAt: now - 60 * 60000, priceChange: { h1: 20 } }, now)).toMatchObject({ pool: true, age: true, ran: true });
  expect(livePips({ liquidity: { usd: GUARD.pool - 1 }, pairCreatedAt: now - 5 * 60000, priceChange: { h1: GUARD.ranH1 + 1 } }, now)).toMatchObject({ pool: false, age: false, ran: false });
  expect(livePips(null)).toBeNull();
  expect(basisOf({ pnlBasis: 'pool' })).toBe('pool'); expect(basisOf({ poolSpentSol: 0.01 })).toBe('pool'); expect(basisOf({ pnlBasis: 'cash (fees in)' })).toBe('cash');
  expect(callWord('picks $BLUE — deep pool')).toBe('PICK'); expect(callWord('agrees: SELL — rolled over')).toBe('SELL'); expect(callWord('on $PIPI: too young')).toBe('READ');
});

test('the dashboard: hero, live prices from our own market proxy (never GeckoTerminal), each tab, a tap opens that folder', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => [{ baseToken: { address: 'MAI' }, priceUsd: '0.0000520', liquidity: { usd: 110000 }, pairCreatedAt: Date.now() - 3600e3, priceChange: { h1: 36 }, marketCap: 320000 },
    { baseToken: { address: 'MAI' }, priceUsd: '0.9', liquidity: { usd: 10 } }] }));
  try { localStorage.removeItem('feeless.powDashTab'); } catch { /* jsdom */ }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onOpen = jest.fn(); const onOlder = jest.fn(); const onCommand = jest.fn();
  await act(async () => root.render(<PowDash folders={FOLDERS} older={3} onOpen={onOpen} onOlder={onOlder} onCommand={onCommand} tools={<i data-testid="tools-in" />} />));
  expect($(el, 'pwd-pnl').textContent).toBe('+0.000695 SOL'); expect($(el, 'pwd-win').textContent).toBe('50%'); expect($(el, 'pwd-open-n').textContent).toBe('1'); expect($(el, 'pwd-stops').textContent).toBe('4');
  const url = String(global.fetch.mock.calls[0][0]); expect(url).toContain('/api/market/tokens/solana/MAI,MPIPI'); expect(url).not.toMatch(/gecko/i);
  await act(async () => { $(el, 'pwd-open-p17').click(); }); expect(onOpen).toHaveBeenLastCalledWith('p17');
  expect($(el, 'pwd-open').querySelector('[data-testid="trc-test"]')).not.toBeNull();   // a TEST proposal says so
  await act(async () => { $(el, 'pwd-tab-watch').click(); });
  expect($(el, 'pwd-px-MAI').textContent).toBe('$0.0000520');   // the deepest pool's price, not the thin one
  expect($(el, 'pwd-px-MPIPI').textContent).toBe('—');
  await act(async () => { $(el, 'pwd-tab-calls').click(); }); await act(async () => { $(el, 'pwd-call-1').click(); }); expect(onOpen).toHaveBeenLastCalledWith('p10');
  await act(async () => { $(el, 'pwd-kpi-guards').click(); }); expect($(el, 'pwd-gbars').textContent).toMatch(/AGE.*1.*POOL.*1.*RAN.*1/);
  await act(async () => { $(el, 'pwd-stop-0').click(); }); expect(onOpen).toHaveBeenLastCalledWith('p17');
  await act(async () => { $(el, 'pwd-tab-filed').click(); }); expect(el.querySelectorAll('[data-testid^="dsk-x-p"]')).toHaveLength(3);
  await act(async () => { $(el, 'dsk-x-old').click(); }); expect(onOlder).toHaveBeenCalled();
  await act(async () => { $(el, 'pwd-tab-tools').click(); }); expect($(el, 'tools-in')).not.toBeNull();
  expect(localStorage.getItem('feeless.powDashTab')).toBe('tools');   // its tab is remembered
  await act(async () => root.unmount()); el.remove();
});

test('nothing open: it says so and the file button only fills the chat box', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => [] }));
  try { localStorage.removeItem('feeless.powDashTab'); } catch { /* jsdom */ }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onCommand = jest.fn();
  await act(async () => root.render(<PowDash folders={[WIN, LOSS]} onOpen={() => {}} onCommand={onCommand} />));
  expect($(el, 'pwd-open-n').textContent).toBe('0');
  await act(async () => { $(el, 'pwd-file').click(); }); expect(onCommand).toHaveBeenCalledWith('file a PoW');
  await act(async () => root.unmount()); el.remove();
});
