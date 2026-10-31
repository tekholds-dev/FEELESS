import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatDesk, deskVitals, curveOf } from './CatDesk';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => null }));   // lightweight-charts is ESM jest can't parse (the desk's live windows load it lazily)
const today = new Date().toISOString().slice(0, 10);
const CAT = { id: 'c1', name: 'Specter', handle: 'specter', avatar: 'Solaris Spots', look: { gear: 'crown', aura: 'gold', eyes: 'laser' }, status: 'running', level: 2, xp: 60, wallet: 'W'.repeat(44),
  balanceSol: 9.6, startingBalanceSol: 10, realizedPnlSol: -0.12, totalPnlSol: -0.08, wins: 3, losses: 5, winRate: 38, strategyLabel: 'Breakouts',
  positions: [{ symbol: 'MOON', pairAddress: 'P1', mint: 'M1', currentChange: 12.5, costSol: 0.25, openedAt: Date.now() / 1000 - 1800, reason: 'germ floor held' }, { symbol: 'RUG', pairAddress: 'P2', currentChange: -20, costSol: 0.2 }],
  pnlHistory: [{ value: 0 }, { value: 0.1 }, { value: -0.2 }, { value: -0.08 }], risk: { maxPositionSol: 0.25, maxDailyLossSol: 0.5, allowlist: [], blocklist: ['SCAM'] },
  dailyLoss: { [today]: 0.4 }, learn: { params: { runnerTrail: 25, takeProfit1: 40 }, log: [{ note: 'Sold $X at +8 %, it ran +60 % — give runners room' }] } };

test('🤖 the desk numbers: today\'s loss against its cap, slots, mood; the P/L curve crosses zero where it should', () => {
  const v = deskVitals(CAT, today);
  expect(v).toMatchObject({ bal: 9.6, start: 10, open: 2, slots: 5, lossToday: 0.4, cap: 0.5, closed: 8, mood: 'pounce' });
  expect(v.capUsed).toBeCloseTo(0.8);
  expect(deskVitals({ ...CAT, status: 'stopped' }).mood).toBe('sleep'); expect(deskVitals({ ...CAT, positions: [], realizedPnlSol: 1 }).mood).toBe('celebrate');
  const c = curveOf(CAT.pnlHistory); expect(c.up).toBe(false); expect(c.line.startsWith('M0.00')).toBe(true); expect(c.zero).toBeGreaterThan(2); expect(c.zero).toBeLessThan(38);
  expect(curveOf([]).line).toContain('M0.00');   // a fresh cat still draws a flat line, never a crash
});

test('🤖 the desk renders an agent HOLDING coins (the old page crashed on a deleted row component), acts, opens a coin\'s war room, saves limits', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn(); const room = jest.fn();
  window.addEventListener('feeless:war-room', room);
  await act(async () => { root.render(<CatDesk cat={CAT} onBack={() => {}} onAct={onAct} Activity={<p data-testid="feed">feed</p>} />); });
  expect(el.querySelector('[data-testid="kd-dl"]').getAttribute('aria-label')).toContain(CAT.name);   // ⬇ its picture as a PNG
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('kd-state').textContent).toContain('HOLDING 2'); expect(el.textContent).toContain('$MOON'); expect(el.textContent).toContain('+12.5%'); expect(el.textContent).toContain('-20.0%');
  expect(el.textContent).toContain('0.400 / 0.5 SOL'); expect(q('feed')).not.toBeNull();
  expect(el.querySelector('.g-crown')).not.toBeNull();                                                   // its built look, drawn
  act(() => q('kd-pos-0').click()); expect(room.mock.calls[0][0].detail).toMatchObject({ pairAddress: 'P1', baseToken: { symbol: 'MOON' } });
  act(() => q('kd-stop').click()); expect(onAct).toHaveBeenLastCalledWith('stop');
  act(() => q('kd-run').click()); expect(onAct).toHaveBeenLastCalledWith('run');
  act(() => q('kd-save').click()); expect(onAct.mock.calls.at(-1)[0]).toBe('controls'); expect(onAct.mock.calls.at(-1)[1]).toMatchObject({ maxPositionSol: 0.25, blocklist: 'SCAM' });
  await act(async () => { root.render(<CatDesk cat={{ ...CAT, status: 'stopped', positions: [] }} onBack={() => {}} onAct={onAct} />); });
  expect(q('kd-state').textContent).toContain('STOPPED'); act(() => q('kd-start').click()); expect(onAct).toHaveBeenLastCalledWith('start');
  window.removeEventListener('feeless:war-room', room); act(() => root.unmount());
});

test('🐱 Fee on her desk: the creator gets her tools, never a button the server only answers 403 to; a visitor just views', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cat: { id: 'leader', positions: [] }, events: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`); const fee = { ...CAT, id: 'leader', name: 'Fee', isLeader: true };
  await act(async () => { root.render(<CatDesk cat={fee} canEdit onBack={() => {}} onAct={() => {}} Tools={<p data-testid="tools">tools</p>} />); });
  expect(q('tools')).not.toBeNull(); expect(q('fee-live')).not.toBeNull(); expect(el.textContent).toContain('YOUR CAT');
  ['kd-stop', 'kd-run', 'kd-save', 'kd-withdraw', 'kd-revoke'].forEach(id => expect(q(id)).toBeNull());
  await act(async () => { root.render(<CatDesk cat={fee} canEdit={false} onBack={() => {}} onAct={() => {}} />); });
  expect(el.textContent).toContain('VIEWING'); expect(el.textContent).not.toContain('YOUR CAT');
  act(() => root.unmount());
});

test('💵 a general agent with a wallet shows its real wallet, credit and coins, never the paper tiles', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ balance: { sol: 0.0266, usdc: 0 } }) }));
  const gen = { ...CAT, brainsCfg: { kind: 'general', brains: ['a/x'], brainMode: 'turns', credit: 12.5, spent: 0.5 }, agentWallet: { address: 'R'.repeat(44), mode: 'approve' }, realHeld: { M1: { symbol: 'JUP', pair: 'P1' } }, agentTx: [{ status: 'success' }, { status: 'failed' }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatDesk cat={gen} canEdit onBack={() => {}} onAct={() => {}} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('kd-real-tiles').textContent).toContain('0.0266 SOL'); expect(q('kd-real-tiles').textContent).toContain('$12.50');
  expect(q('kd-real-holds').textContent).toContain('$JUP'); expect(q('kd-wallet').textContent).toContain('ITS WALLET'); expect(q('kd-curve')).toBeNull(); expect(el.textContent).not.toContain('PAPER WALLET');
  act(() => root.unmount());
});

test('⬇ the desk has a download button on its picture; the file name is the agent\'s', () => {
  const { fileName, inlineSvg } = require('../../lib/svgPng');
  expect(fileName('Night Claw')).toBe('night-claw-feeless.png'); expect(fileName('')).toBe('agent-feeless.png');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 10 20'); svg.setAttribute('class', 'x');
  const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.style.fill = 'rgb(179, 136, 255)'; svg.appendChild(c); document.body.appendChild(svg);
  const out = inlineSvg(svg, 512);
  expect(out).toContain('width="512"'); expect(out).toContain('height="1024"'); expect(out).toContain('fill: rgb(179, 136, 255)'); expect(out).not.toContain('class="x"');
  svg.remove();
});
