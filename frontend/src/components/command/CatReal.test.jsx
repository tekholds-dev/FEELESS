import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { realView, CatReal } from './CatReal';

const mockSwap = jest.fn();
jest.mock('../FamiliaTrade', () => ({ familiaSwap: (...a) => mockSwap(...a), FamiliaTradeDock: () => null }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({}) }));
global.IS_REACT_ACT_ENVIRONMENT = true;

const NOW = Math.floor(Date.now() / 1000);   // the panel reads the real clock
const DEV = 'DEV1111111111111111111111111111111111111111';
const rec = { trades: 4, wonPct: 75, pnlSol: 0.12 };
const real = { id: 'c1', name: 'Mittens', mode: 'real', realWallet: DEV, budgetSol: 0.05, realHeld: { M1: { symbol: 'AAA' } }, proposals: [
  { id: 'old', side: 'buy', mint: 'M1', symbol: 'AAA', at: NOW - 900, until: NOW - 10, status: 'pending', sol: 0.05, record: rec },
  { id: 'b1', side: 'buy', mint: 'M2', symbol: 'BBB', why: 'buyers lead', at: NOW - 30, until: NOW + 870, status: 'pending', sol: 0.05, record: rec },
  { id: 's1', side: 'sell', mint: 'M1', symbol: 'AAA', at: NOW - 60, until: NOW + 840, status: 'pending', fraction: 0.5, record: rec },
  { id: 'd1', side: 'buy', mint: 'M1', symbol: 'AAA', at: NOW - 2000, until: NOW - 1100, status: 'done', sig: 'S', sol: 0.05, record: rec }] };

test('realView: pending first and newest first; a stale pending reads as expired with no time left', () => {
  const v = realView(real, NOW);
  expect(v.real).toBe(true);
  expect(v.list.map(p => p.id)).toEqual(['b1', 's1', 'old', 'd1']);
  expect(v.list[2].status).toBe('expired');
  expect(v.pending).toBe(2);
  expect(v.list[0].left).toBe(870);
  expect(v.held).toEqual([{ mint: 'M1', symbol: 'AAA' }]);
  expect(realView({ mode: 'real' }).real).toBe(false);
});

function mount(cat, onAct) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => { root.render(<CatReal cat={cat} onAct={onAct} devAddress={DEV} />); });
  return { el, root };
}

test('paper: pick a budget, then go real signs in with the wallet and asks for that budget', async () => {
  const onAct = jest.fn(async () => {});
  const { el, root } = mount({ id: 'c1', name: 'Mittens', wins: 3, losses: 1, winRate: 75, realizedPnlSol: 0.12 }, onAct);
  expect(el.textContent).toContain('4 trades · 75% won');
  act(() => { el.querySelector('[data-testid="cr-b-0.25"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cr-go"]').click(); });
  expect(onAct).toHaveBeenCalledWith('real', { address: DEV, session: 'dev', budgetSol: 0.25 });
  act(() => root.unmount());
});

test('real: sign opens the swap with the coins + amount set; a confirmed trade marks it done; skip answers it', async () => {
  const onAct = jest.fn(async () => {});
  const { el, root } = mount(real, onAct);
  act(() => { el.querySelector('[data-testid="cr-sign-b1"]').click(); });
  expect(mockSwap).toHaveBeenCalledWith(expect.objectContaining({ from: 'So11111111111111111111111111111111111111112', to: 'M2', amount: 0.05 }));
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint: 'M9', side: 'buy', signature: 'X' } })); });
  expect(onAct).not.toHaveBeenCalled();                                   // another coin's trade is not this proposal
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint: 'M2', side: 'buy', signature: 'SIG' } })); });
  expect(onAct).toHaveBeenCalledWith('proposal', { address: DEV, session: 'dev', proposal: 'b1', result: 'done', sig: 'SIG' });
  act(() => { el.querySelector('[data-testid="cr-sign-s1"]').click(); });
  expect(mockSwap).toHaveBeenLastCalledWith(expect.objectContaining({ from: 'M1', pct: 0.5 }));
  await act(async () => { el.querySelector('[data-testid="cr-skip-s1"]').click(); });
  expect(onAct).toHaveBeenLastCalledWith('proposal', { address: DEV, session: 'dev', proposal: 's1', result: 'skip' });
  act(() => root.unmount());
});

test('👛 its own wallet: make it (signed), then live SOL / USDC + copy; a general cat switches ASK ME / DO ITS THING, a trading cat just rides', async () => {
  global.fetch = async () => ({ ok: true, json: async () => ({ wallet: { address: 'AGT1111111111111111111111111111111111111111', mode: 'approve' }, balance: { sol: 0.25, usdc: 3.5 } }) });
  const onAct = jest.fn(async () => {});
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatReal cat={{ id: 'g1', name: 'Gen', brainsCfg: { kind: 'general' } }} onAct={onAct} devAddress={DEV} />); });
  await act(async () => { el.querySelector('[data-testid="cr-agent-make"]').click(); });
  expect(onAct).toHaveBeenCalledWith('agent_wallet', { address: DEV, session: 'dev' });
  const made = { id: 'g1', name: 'Gen', brainsCfg: { kind: 'general' }, agentWallet: { address: 'AGT1111111111111111111111111111111111111111', mode: 'approve' } };
  await act(async () => { root.render(<CatReal cat={made} onAct={onAct} devAddress={DEV} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const card = el.querySelector('[data-testid="cr-agent"]');
  expect(card.textContent).toContain('0.2500'); expect(card.textContent).toContain('3.50'); expect(card.textContent).toContain('FUNDED');
  await act(async () => { el.querySelector('[data-testid="cr-agent-auto"]').click(); });
  expect(onAct).toHaveBeenLastCalledWith('agent_mode', { address: DEV, session: 'dev', mode: 'auto' });
  await act(async () => { root.render(<CatReal cat={{ ...made, brainsCfg: { kind: 'trading' }, agentWallet: { ...made.agentWallet, mode: 'auto' } }} onAct={onAct} devAddress={DEV} />); });
  expect(el.querySelector('[data-testid="cr-agent-auto"]')).toBeNull(); expect(el.querySelector('[data-testid="cr-agent"]').textContent).toContain('RIDES');
  await act(async () => { root.unmount(); });
});
