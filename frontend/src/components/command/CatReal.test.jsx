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

test('🏇 a cat with its own wallet: ASK ME shows ✅ Approve (no ✍ Sign it), auto shows it sending, and the day bar counts its buys', async () => {
  global.fetch = async () => ({ ok: true, json: async () => ({ balance: { sol: 1, usdc: 0 } }) });
  const onAct = jest.fn(async () => {});
  const p = { id: 'q1', side: 'buy', mint: 'M2', symbol: 'NEXT', at: NOW - 30, until: NOW + 870, status: 'pending', sol: 0.05, record: rec };
  const ask = { id: 'g1', name: 'Gen', mode: 'real', realWallet: DEV, budgetSol: 0.05, brainsCfg: { kind: 'general' }, proposals: [p],
    agentWallet: { address: 'AGT1111111111111111111111111111111111111111', mode: 'approve' }, agentTx: [{ side: 'buy', sol: 0.05, status: 'success', at: NOW - 100 }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatReal cat={ask} onAct={onAct} devAddress={DEV} />); });
  expect(el.querySelector('[data-testid="cr-sign-q1"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="cr-approve-q1"]').click(); });
  expect(onAct).toHaveBeenLastCalledWith('agent_approve', { address: DEV, session: 'dev', proposal: 'q1' });
  expect(el.querySelector('[data-testid="cr-agent-day"]').textContent).toContain('0.05 / 0.2 SOL');
  await act(async () => { root.render(<CatReal cat={{ ...ask, agentWallet: { ...ask.agentWallet, mode: 'auto' }, proposals: [{ ...p, agentWhy: 'its daily cap is 0.2 SOL' }] }} onAct={onAct} devAddress={DEV} />); });
  expect(el.querySelector('[data-testid="cr-approve-q1"]')).toBeNull(); expect(el.textContent).toContain('⏸ its daily cap is 0.2 SOL');
  expect(el.querySelector('header').textContent).toContain('no signing per trade');
  await act(async () => { root.unmount(); });
});

test('💵 FUND IT: any amount → a receipt (you pay · FEELESS one-time · into its wallet) → your wallet signs that exact tx → sent', async () => {
  const { FundCat } = require('./CatReal');
  const calls = []; localStorage.setItem('feeless.recoverySaved.' + 'c1', '1');   // 🔐 the owner already confirmed the recovery phrase
  global.fetch = async (u, o = {}) => { calls.push([String(u), o.body ? JSON.parse(o.body) : null]);
    if (String(u).endsWith('/fund')) return { ok: true, json: async () => ({ plan: { usd: 25, feeUsd: 2, catUsd: 23, solUsd: 200, totalLamports: 125e6, feeLamports: 10e6, catLamports: 115e6 }, transaction: 'TXB64', expiresIn: 90 }) };
    return { ok: true, json: async () => ({ state: 'confirmed', signature: 'SIG12345678' }) }; };
  const sign = jest.fn(async b => `signed:${b}`); const session = jest.fn(async () => 'sess');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FundCat cat={{ id: 'c1' }} addr={DEV} session={session} sign={sign} />); });
  expect([...el.querySelectorAll('[data-testid^="cr-fund-"][role="radio"]')].map(b => b.textContent)).toEqual(['$10', '$25', '$50', '$100']);   // first funding: $10+
  await act(async () => { el.querySelector('[data-testid="cr-fund-25"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cr-fund-quote"]').click(); });
  const posts = () => calls.filter(c => c[1]);
  expect(calls[0][0]).toContain('/cats/fund-rules?address=');                                                      // the rules come first
  expect(posts()[0][1]).toEqual({ address: DEV, session: 'sess', usd: 25 });
  const r = el.querySelector('[data-testid="cr-receipt"]').textContent;
  expect(r).toContain('$25.00'); expect(r).toContain('$2.00'); expect(r).toContain('$23.00'); expect(r).toContain('0.1150 SOL');
  await act(async () => { el.querySelector('[data-testid="cr-fund-sign"]').click(); });
  expect(sign).toHaveBeenCalledWith('TXB64'); expect(posts()[1][0]).toContain('/cats/c1/fund/send'); expect(posts()[1][1]).toEqual({ address: DEV, session: 'sess', signed: 'signed:TXB64' });
  expect(el.querySelector('[data-testid="cr-fund-done"]').textContent).toContain('✓ funded');
  await act(async () => { root.render(<FundCat cat={{ id: 'c1', agentFunded: [{ sig: 'S' }] }} addr={DEV} session={session} sign={sign} />); });
  await act(async () => { root.unmount(); });
});

test('💵 the warning before a receipt: an amount that only covers the fee says so; staff pay no fee', () => {
  const { fundWarn } = require('./CatReal');
  const R = { feeUsd: 2, minUsd: 10, topupMinUsd: 1 };
  expect(fundWarn(2, R, true)).toContain('only covers the $2 one-time fee'); expect(fundWarn(1, R, true)).toContain('only covers');
  expect(fundWarn(6, R, true)).toContain('starts at $10'); expect(fundWarn(10, R, true)).toBeNull();
  expect(fundWarn(0.5, R, false)).toContain('A top-up starts at $1'); expect(fundWarn(3, R, false)).toBeNull();
  expect(fundWarn(1, { feeUsd: 0, minUsd: 1, topupMinUsd: 1, staff: true }, true)).toBeNull();                        // the creator tests with $1, no fee
});

test('👛 N16 Fee takes an assigned wallet: the field posts agent_assign; a watch-only wallet says so and offers no funding', async () => {
  global.fetch = async () => ({ ok: true, json: async () => ({ balance: { sol: 2, usdc: 0 } }) });
  const onAct = jest.fn(async () => {});
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatReal cat={{ id: 'leader', name: 'Fee', isLeader: true }} onAct={onAct} devAddress={DEV} />); });
  const inp = el.querySelector('[data-testid="cr-assign-in"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cr-assign-go"]').click(); });
  expect(onAct).toHaveBeenLastCalledWith('agent_assign', { address: DEV, session: 'dev', text: 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P' });
  await act(async () => { root.render(<CatReal cat={{ id: 'leader', name: 'Fee', isLeader: true, agentWallet: { address: 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P', provider: 'watch', mode: 'auto', assigned: true } }} onAct={onAct} devAddress={DEV} />); });
  expect(el.querySelector('[data-testid="cr-agent-watch"]')).not.toBeNull(); expect(el.querySelector('[data-testid="cr-fund"]')).toBeNull();
  await act(async () => { root.render(<CatReal cat={{ id: 'u1', name: 'Mine' }} onAct={onAct} devAddress={DEV} />); });
  expect(el.querySelector('[data-testid="cr-assign"]')).toBeNull();                                                        // a user's cat: a fresh wallet only
  await act(async () => { root.unmount(); });
});
